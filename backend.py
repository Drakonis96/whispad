from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import os
import io
import zipfile
import re
import requests
import json
import time
import threading
from dotenv import load_dotenv
import tempfile
import base64
import re
from datetime import datetime
from whisper_cpp_wrapper import WhisperCppWrapper
from sensevoice_wrapper import get_sensevoice_wrapper

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Allow uploads up to 4GB for large whisper.cpp models
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4GB
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# Configurar CORS para permitir acceso desde el frontend
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,https://localhost:5037').split(',')
CORS(app, origins=cors_origins)

# Configuración de APIs
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Inicializar el wrapper de whisper.cpp local
try:
    whisper_wrapper = WhisperCppWrapper()
    WHISPER_CPP_AVAILABLE = whisper_wrapper.is_ready()
    print(f"Whisper.cpp local available: {WHISPER_CPP_AVAILABLE}")
except Exception as e:
    print(f"Error initializing whisper.cpp: {e}")
    WHISPER_CPP_AVAILABLE = False
    whisper_wrapper = None

# Inicializar el wrapper de SenseVoice
try:
    sensevoice_wrapper = get_sensevoice_wrapper()
    SENSEVOICE_AVAILABLE = sensevoice_wrapper.is_available()
    print(f"SenseVoice available: {SENSEVOICE_AVAILABLE}")
except Exception as e:
    print(f"Error initializing SenseVoice: {e}")
    SENSEVOICE_AVAILABLE = False
    sensevoice_wrapper = None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el backend está funcionando"""
    return jsonify({"status": "ok", "message": "Backend funcionando correctamente"})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Endpoint para transcribir audio usando OpenAI o whisper.cpp local"""
    try:
        # Obtener el archivo de audio del request
        if 'audio' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Archivo de audio vacío"}), 400
        
        # Obtener parámetros del request
        language = request.form.get('language', None)  # None = detección automática
        provider = request.form.get('provider', 'openai')  # openai o local
        model_name = request.form.get('model')
        
        # Verificar disponibilidad del proveedor
        if provider == 'local':
            if not WHISPER_CPP_AVAILABLE:
                return jsonify({"error": "Whisper.cpp local no está disponible"}), 500
            
            # Usar whisper.cpp local
            audio_bytes = audio_file.read()

            model_path = None
            if model_name:
                models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
                model_path = os.path.join(models_dir, os.path.basename(model_name))

            result = whisper_wrapper.transcribe_audio_from_bytes(
                audio_bytes,
                audio_file.filename,
                language,
                model_path
            )
            
            if result.get('success'):
                return jsonify({
                    "transcription": result.get('transcription', ''),
                    "provider": "local",
                    "model": result.get('model', 'whisper-tiny-local')
                })
            else:
                return jsonify({"error": f"Error en transcripción local: {result.get('error', 'Unknown error')}"}), 500
        
        elif provider == 'sensevoice':
            if not SENSEVOICE_AVAILABLE:
                return jsonify({"error": "SenseVoice no está disponible. Asegúrate de haber descargado el modelo SenseVoiceSmall."}), 500
            
            # Usar SenseVoice
            audio_bytes = audio_file.read()
            
            # Obtener opciones adicionales
            detect_emotion = request.form.get('detect_emotion', 'true').lower() == 'true'
            detect_events = request.form.get('detect_events', 'true').lower() == 'true'
            use_itn = request.form.get('use_itn', 'true').lower() == 'true'
            
            result = sensevoice_wrapper.transcribe_audio_from_bytes(
                audio_bytes,
                audio_file.filename,
                language,
                detect_emotion=detect_emotion,
                detect_events=detect_events,
                use_itn=use_itn
            )
            
            if result.get('success'):
                response_data = {
                    "transcription": result.get('transcription', ''),
                    "provider": "sensevoice",
                    "model": result.get('model', 'SenseVoiceSmall'),
                    "language_detected": result.get('language_detected'),
                }
                
                # Agregar información adicional si está disponible
                if result.get('emotion'):
                    response_data["emotion"] = result.get('emotion')
                if result.get('events'):
                    response_data["events"] = result.get('events')
                
                return jsonify(response_data)
            else:
                return jsonify({"error": f"Error en transcripción SenseVoice: {result.get('error', 'Unknown error')}"}), 500
                
        else:  # OpenAI
            if not OPENAI_API_KEY:
                return jsonify({"error": "API key de OpenAI no configurada"}), 500
            
            # Preparar la petición a OpenAI
            files = {
                'file': (audio_file.filename, audio_file.stream, audio_file.content_type),
                'model': (None, 'whisper-1')
            }
            
            # Solo añadir language si se especifica (None = auto-detectar)
            if language and language != 'auto':
                files['language'] = (None, language)
            
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}'
            }
            
            response = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                files=files,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    "transcription": result.get('text', ''),
                    "provider": "openai",
                    "model": "whisper-1"
                })
            else:
                return jsonify({"error": "Error en la transcripción"}), response.status_code
            
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/api/improve-text', methods=['POST'])
def improve_text():
    """Endpoint para mejorar texto usando OpenAI o Google AI"""
    try:
        data = request.get_json()
        if not data or 'text' not in data or 'improvement_type' not in data:
            return jsonify({"error": "Faltan parámetros requeridos"}), 400
        
        text = data['text']
        improvement_type = data['improvement_type']
        provider = data.get('provider', 'openai')  # openai o google
        stream = data.get('stream', False)  # Nuevo parámetro para streaming
        custom_prompt = data.get('custom_prompt')  # Nuevo parámetro para prompts personalizados
        
        if stream:
            if provider == 'openai':
                return improve_text_openai_stream(text, improvement_type, custom_prompt)
            elif provider == 'google':
                return improve_text_google_stream(text, improvement_type, custom_prompt)
            elif provider == 'openrouter':
                model = data.get('model', 'google/gemma-3-27b-it:free')
                return improve_text_openrouter_stream(text, improvement_type, model, custom_prompt)
            else:
                return jsonify({"error": "Proveedor no soportado para streaming"}), 400
        else:
            if provider == 'openai':
                return improve_text_openai(text, improvement_type, custom_prompt)
            elif provider == 'google':
                return improve_text_google(text, improvement_type, custom_prompt)
            elif provider == 'openrouter':
                model = data.get('model', 'google/gemma-3-27b-it:free')
                return improve_text_openrouter(text, improvement_type, model, custom_prompt)
            else:
                return jsonify({"error": "Proveedor no soportado"}), 400
            
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def improve_text_openai(text, improvement_type, custom_prompt=None):
    """Mejorar texto usando OpenAI"""
    if not OPENAI_API_KEY:
        return jsonify({"error": "API key de OpenAI no configurada"}), 500
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'claridad': f"Reescribe el siguiente texto de manera más clara y legible. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'formal': f"Reescribe el siguiente texto en un tono formal. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'casual': f"Reescribe el siguiente texto en un tono casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'academico': f"Reescribe el siguiente texto en estilo académico. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'narrativo': f"Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'academico_v2': f"Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'resumir': f"Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el resumen, sin explicaciones adicionales:\n\n{text}",
            'expandir': f"Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto expandido, sin explicaciones adicionales:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Mejora el siguiente texto: {text}")
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': 1000,
        'temperature': 0.7
    }
    
    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        improved_text = result['choices'][0]['message']['content']
        return jsonify({"improved_text": improved_text})
    else:
        return jsonify({"error": "Error al mejorar el texto"}), response.status_code

def improve_text_google(text, improvement_type, custom_prompt=None):
    """Mejorar texto usando Google AI (Gemini)"""
    if not GOOGLE_API_KEY:
        return jsonify({"error": "API key de Google no configurada"}), 500
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'claridad': f"Reescribe el siguiente texto de manera más clara y legible. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'formal': f"Reescribe el siguiente texto en un tono formal. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'casual': f"Reescribe el siguiente texto en un tono casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'academico': f"Reescribe el siguiente texto en estilo académico. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'narrativo': f"Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'academico_v2': f"Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'resumir': f"Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el resumen, sin explicaciones adicionales:\n\n{text}",
            'expandir': f"Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto expandido, sin explicaciones adicionales:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Mejora el siguiente texto: {text}")
    
    # Nueva URL según la documentación oficial de Gemini
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        improved_text = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"improved_text": improved_text})
    else:
        return jsonify({"error": "Error al mejorar el texto con Google AI"}), response.status_code

def improve_text_openai_stream(text, improvement_type, custom_prompt=None):
    """Mejorar texto usando OpenAI con streaming"""
    if not OPENAI_API_KEY:
        return jsonify({"error": "API key de OpenAI no configurada"}), 500
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'claridad': f"Reescribe el siguiente texto de manera más clara y legible. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'formal': f"Reescribe el siguiente texto en un tono formal. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'casual': f"Reescribe el siguiente texto en un tono casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'academico': f"Reescribe el siguiente texto en estilo académico. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'narrativo': f"Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'academico_v2': f"Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'resumir': f"Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el resumen, sin explicaciones adicionales:\n\n{text}",
            'expandir': f"Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto expandido, sin explicaciones adicionales:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Mejora el siguiente texto: {text}")
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': 1000,
        'temperature': 0.7,
        'stream': True
    }
    
    def generate():
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': 'Error al mejorar el texto'})}\n\n"
                return
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() == '[DONE]':
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def improve_text_google_stream(text, improvement_type, custom_prompt=None):
    """Mejorar texto usando Google AI con streaming (simulado)"""
    if not GOOGLE_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de Google no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
    
    # Google AI no soporta streaming nativamente, así que simularemos
    # Primero obtenemos la respuesta completa
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'claridad': f"Reescribe el siguiente texto de manera más clara y legible. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'formal': f"Reescribe el siguiente texto en un tono formal. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'casual': f"Reescribe el siguiente texto en un tono casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'academico': f"Reescribe el siguiente texto en estilo académico. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'narrativo': f"Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'academico_v2': f"Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'resumir': f"Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el resumen, sin explicaciones adicionales:\n\n{text}",
            'expandir': f"Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto expandido, sin explicaciones adicionales:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Mejora el siguiente texto: {text}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }
    
    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_msg = f"Error de Google API: {response.status_code}"
                if response.content:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', error_msg)
                    except:
                        pass
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
            
            result = response.json()
            if 'candidates' not in result or not result['candidates']:
                yield f"data: {json.dumps({'error': 'No se recibió respuesta válida de Google AI'})}\n\n"
                return
                
            improved_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Simular streaming enviando palabras de a una
            import time
            words = improved_text.split(' ')
            for i, word in enumerate(words):
                if i == 0:
                    yield f"data: {json.dumps({'content': word})}\n\n"
                else:
                    yield f"data: {json.dumps({'content': ' ' + word})}\n\n"
                time.sleep(0.1)  # Pausa pequeña para simular streaming
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except requests.RequestException as e:
            yield f"data: {json.dumps({'error': f'Error de conexión con Google API: {str(e)}'})}\n\n"
        except KeyError as e:
            yield f"data: {json.dumps({'error': f'Respuesta inesperada de Google API: {str(e)}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error interno: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def improve_text_openrouter(text, improvement_type, model='google/gemma-3-27b-it:free', custom_prompt=None):
    """Mejorar texto usando OpenRouter"""
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "API key de OpenRouter no configurada"}), 500
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'claridad': f"Reescribe el siguiente texto de manera más clara y legible. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'formal': f"Reescribe el siguiente texto en un tono formal. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'casual': f"Reescribe el siguiente texto en un tono casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'academico': f"Reescribe el siguiente texto en estilo académico. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'narrativo': f"Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'academico_v2': f"Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'resumir': f"Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el resumen, sin explicaciones adicionales:\n\n{text}",
            'expandir': f"Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto expandido, sin explicaciones adicionales:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Mejora el siguiente texto: {text}")
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://note-transcribe-ai.local',
        'X-Title': 'Note Transcribe AI'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': 1000,
        'temperature': 0.7
    }
    
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            improved_text = result['choices'][0]['message']['content']
            return jsonify({"improved_text": improved_text})
        else:
            error_msg = f"Error de OpenRouter API: {response.status_code}"
            if response.content:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', error_msg)
                except:
                    pass
            return jsonify({"error": error_msg}), response.status_code
            
    except requests.RequestException as e:
        return jsonify({"error": f"Error de conexión con OpenRouter API: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def improve_text_openrouter_stream(text, improvement_type, model='google/gemma-3-27b-it:free', custom_prompt=None):
    """Mejorar texto usando OpenRouter con streaming"""
    if not OPENROUTER_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de OpenRouter no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'claridad': f"Reescribe el siguiente texto de manera más clara y legible. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'formal': f"Reescribe el siguiente texto en un tono formal. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'casual': f"Reescribe el siguiente texto en un tono casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'academico': f"Reescribe el siguiente texto en estilo académico. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto reescrito, sin explicaciones adicionales:\n\n{text}",
            'narrativo': f"Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'academico_v2': f"Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible. Responde ÚNICAMENTE con el texto mejorado, sin explicaciones adicionales:\n\n{text}",
            'resumir': f"Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el resumen, sin explicaciones adicionales:\n\n{text}",
            'expandir': f"Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Responde ÚNICAMENTE con el texto expandido, sin explicaciones adicionales:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Mejora el siguiente texto: {text}")
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://note-transcribe-ai.local',
        'X-Title': 'Note Transcribe AI'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': 1000,
        'temperature': 0.7,
        'stream': True
    }
    
    def generate():
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                error_msg = f"Error de OpenRouter API: {response.status_code}"
                if response.content:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', error_msg)
                    except:
                        pass
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() == '[DONE]':
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
                            
        except requests.RequestException as e:
            yield f"data: {json.dumps({'error': f'Error de conexión con OpenRouter API: {str(e)}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error interno: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

@app.route('/api/transcribe-gpt4o', methods=['POST'])
def transcribe_audio_gpt4o():
    """Endpoint para transcribir audio usando GPT-4o transcription models con soporte para streaming"""
    try:
        print(f"[DEBUG] Iniciando transcripción GPT-4o...")
        
        if not OPENAI_API_KEY:
            print(f"[ERROR] API key de OpenAI no configurada")
            return jsonify({"error": "API key de OpenAI no configurada"}), 500
        
        # Obtener el archivo de audio del request
        if 'audio' not in request.files:
            print(f"[ERROR] No se encontró archivo de audio en la petición")
            return jsonify({"error": "No se encontró archivo de audio"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            print(f"[ERROR] Archivo de audio vacío")
            return jsonify({"error": "Archivo de audio vacío"}), 400
        
        # Obtener parámetros del request
        model = request.form.get('model', 'gpt-4o-mini-transcribe')  # Por defecto gpt-4o-mini-transcribe
        language = request.form.get('language', None)  # None = detección automática
        prompt = request.form.get('prompt', None)  # Prompt para mejorar transcripción
        response_format = request.form.get('response_format', 'json')  # json o text
        stream = request.form.get('stream', 'false').lower() == 'true'
        
        print(f"[DEBUG] Parámetros recibidos:")
        print(f"  - Model: {model}")
        print(f"  - Language: {language}")
        print(f"  - Response format: {response_format}")
        print(f"  - Stream: {stream} (NOTA: OpenAI no soporta streaming para transcripciones)")
        print(f"  - Prompt: {prompt}")
        print(f"  - Archivo: {audio_file.filename}, tamaño: {audio_file.content_length}")
        
        # Forzar stream=False porque OpenAI no soporta streaming para transcripciones
        if stream:
            print(f"[WARNING] Streaming solicitado pero no soportado por OpenAI para transcripciones. Usando modo normal.")
            stream = False
        
        # Validar modelo
        if model not in ['gpt-4o-transcribe', 'gpt-4o-mini-transcribe']:
            print(f"[ERROR] Modelo no válido: {model}")
            return jsonify({"error": "Modelo no válido. Use 'gpt-4o-transcribe' o 'gpt-4o-mini-transcribe'"}), 400
        
        # Validar formato de respuesta
        if response_format not in ['json', 'text']:
            print(f"[ERROR] Formato de respuesta no válido: {response_format}")
            return jsonify({"error": "Formato de respuesta no válido. Use 'json' o 'text'"}), 400
        
        # Preparar la petición a OpenAI
        files = {
            'file': (audio_file.filename, audio_file.stream, audio_file.content_type),
            'model': (None, model),
            'response_format': (None, response_format)
        }
        
        # Añadir parámetros opcionales
        if language and language != 'auto':
            files['language'] = (None, language)
        
        if prompt:
            files['prompt'] = (None, prompt)
        
        # NO añadir stream porque OpenAI no lo soporta para transcripciones
        
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}'
        }
        
        print(f"[DEBUG] Enviando petición a OpenAI API...")
        print(f"  - URL: https://api.openai.com/v1/audio/transcriptions")
        print(f"  - Files: {list(files.keys())}")
        
        print(f"[DEBUG] Usando modo normal (OpenAI no soporta streaming para transcripciones)")
        # Manejar respuesta normal
        response = requests.post(
            'https://api.openai.com/v1/audio/transcriptions',
            files=files,
            headers=headers
        )
        
        print(f"[DEBUG] Respuesta de OpenAI: {response.status_code}")
        if response.status_code != 200:
            error_text = response.text
            print(f"[ERROR] Error en respuesta de OpenAI: {error_text}")
            try:
                error_json = response.json()
                print(f"[ERROR] Error JSON: {error_json}")
                return jsonify({"error": f"Error en la transcripción - {error_json.get('error', {}).get('message', error_text)}"}), response.status_code
            except:
                return jsonify({"error": f"Error en la transcripción - {error_text}"}), response.status_code
        
        if response_format == 'text':
            # Para formato text, la respuesta es directamente el texto
            transcription_text = response.text
            print(f"[DEBUG] Transcripción (text): {transcription_text[:100]}...")
            return jsonify({"transcription": transcription_text})
        else:
            # Para formato json
            result = response.json()
            transcription_text = result.get('text', '')
            print(f"[DEBUG] Transcripción (json): {transcription_text[:100]}...")
            return jsonify({"transcription": transcription_text})
            
    except Exception as e:
        print(f"[ERROR] Error interno en transcripción GPT-4o: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def stream_transcription_response(response):
    """Generador para procesar respuesta de streaming de transcripción"""
    try:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # Procesar eventos de streaming
                if decoded_line.startswith('data: '):
                    data = decoded_line[6:]  # Remover 'data: '
                    if data.strip() == '[DONE]':
                        break
                    try:
                        event_data = json.loads(data)
                        # Enviar el delta de texto si está disponible
                        if 'text' in event_data:
                            yield f"data: {json.dumps({'text': event_data['text']})}\n\n"
                        elif 'delta' in event_data:
                            yield f"data: {json.dumps({'delta': event_data['delta']})}\n\n"
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route('/api/save-note', methods=['POST'])
def save_note():
    """Endpoint para guardar una nota como archivo .md en el directorio saved_notes"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        note_id = data.get('id', '')
        tags = data.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip().lower() for t in tags.split(';') if t.strip()]
        elif isinstance(tags, list):
            tags = [str(t).strip().lower() for t in tags if str(t).strip()]
        else:
            tags = []
        
        if not note_id:
            return jsonify({"error": "Se requiere un ID de nota"}), 400
        
        if not title and not content:
            return jsonify({"error": "La nota debe tener al menos un título o contenido"}), 400
        
        # Crear directorio saved_notes si no existe
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        os.makedirs(saved_notes_dir, exist_ok=True)
        
        # Generar nombre de archivo seguro basado en el título
        if not title:
            title = "Nota sin título"
        
        safe_filename = generate_safe_filename(title)
        new_filename = f"{safe_filename}.md"
        new_filepath = os.path.join(saved_notes_dir, new_filename)
        
        # Buscar archivo existente para esta nota
        existing_filepath = find_existing_note_file(saved_notes_dir, note_id)
        
        # Si existe un archivo pero el nombre ha cambiado, renombrarlo
        if existing_filepath and existing_filepath != new_filepath:
            # Si el nuevo nombre ya existe y no es el archivo actual, agregar sufijo
            if os.path.exists(new_filepath):
                counter = 1
                while True:
                    name_without_ext = os.path.splitext(new_filename)[0]
                    temp_filename = f"{name_without_ext}-{counter}.md"
                    temp_filepath = os.path.join(saved_notes_dir, temp_filename)
                    if not os.path.exists(temp_filepath):
                        new_filename = temp_filename
                        new_filepath = temp_filepath
                        break
                    counter += 1
            
            # Renombrar el archivo existente junto con su metadata
            try:
                os.rename(existing_filepath, new_filepath)
                old_meta = f"{existing_filepath}.meta"
                new_meta = f"{new_filepath}.meta"
                if os.path.exists(old_meta):
                    # Si ya existe un meta con el nuevo nombre, elimínalo para evitar duplicados
                    if os.path.exists(new_meta):
                        os.remove(new_meta)
                    os.rename(old_meta, new_meta)
            except OSError as e:
                return jsonify({"error": f"Error al renombrar archivo: {str(e)}"}), 500
        
        # Si no existe archivo para esta nota, crear uno nuevo
        elif not existing_filepath:
            # Verificar que el nombre no esté en uso
            if os.path.exists(new_filepath):
                counter = 1
                while True:
                    name_without_ext = os.path.splitext(new_filename)[0]
                    temp_filename = f"{name_without_ext}-{counter}.md"
                    temp_filepath = os.path.join(saved_notes_dir, temp_filename)
                    if not os.path.exists(temp_filepath):
                        new_filename = temp_filename
                        new_filepath = temp_filepath
                        break
                    counter += 1
        else:
            # El archivo existe y el nombre no ha cambiado
            new_filepath = existing_filepath
            new_filename = os.path.basename(new_filepath)
        
        # Convertir HTML a Markdown básico si es necesario
        markdown_content = html_to_markdown(content) if content else ""
        
        # Crear contenido del archivo markdown
        file_content = f"# {title}\n\n"
        if markdown_content:
            file_content += markdown_content
        else:
            file_content += "*Esta nota está vacía*\n"

        # Guardar el archivo markdown
        with open(new_filepath, 'w', encoding='utf-8') as f:
            f.write(file_content)

        # Guardar metadata en un archivo paralelo .meta
        meta_filepath = f"{new_filepath}.meta"
        metadata = {
            "id": note_id,
            "title": title,
            "updated": datetime.now().isoformat(),
            "tags": tags
        }
        with open(meta_filepath, 'w', encoding='utf-8') as meta_file:
            json.dump(metadata, meta_file, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": "Nota guardada correctamente",
            "filename": new_filename,
            "filepath": new_filepath
        })
        
    except Exception as e:
        return jsonify({"error": f"Error al guardar la nota: {str(e)}"}), 500

def generate_safe_filename(title):
    """Genera un nombre de archivo seguro a partir del título"""
    # Reemplazar caracteres no permitidos
    safe_filename = re.sub(r'[^\w\s-]', '', title)
    safe_filename = re.sub(r'[-\s]+', '-', safe_filename).strip('-')
    
    # Si el nombre está vacío después de la limpieza, usar timestamp
    if not safe_filename:
        safe_filename = f"nota-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Limitar longitud del nombre de archivo
    if len(safe_filename) > 50:
        safe_filename = safe_filename[:50].rstrip('-')
    
    return safe_filename

def find_existing_note_file(saved_notes_dir, note_id):
    """Busca un archivo existente que contenga el ID de nota especificado"""
    try:
        for filename in os.listdir(saved_notes_dir):
            if filename.endswith('.meta'):
                meta_path = os.path.join(saved_notes_dir, filename)
                try:
                    with open(meta_path, 'r', encoding='utf-8') as meta_file:
                        data = json.load(meta_file)
                    if str(data.get('id')) == str(note_id):
                        # remove both .meta and .md extensions to get base name
                        base = os.path.splitext(os.path.splitext(filename)[0])[0]
                        md_file = os.path.join(saved_notes_dir, f"{base}.md")
                        if os.path.exists(md_file):
                            return md_file
                except Exception:
                    continue
        return None
    except OSError:
        return None

def html_to_markdown(html_content):
    """Convierte HTML básico a Markdown"""
    if not html_content:
        return ""
    
    # Reemplazos básicos de HTML a Markdown
    markdown = html_content
    
    # Títulos
    markdown = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', markdown, flags=re.IGNORECASE | re.DOTALL)
    
    # Formateo de texto
    markdown = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<u[^>]*>(.*?)</u>', r'<u>\1</u>', markdown, flags=re.IGNORECASE | re.DOTALL)
    
    # Listas
    markdown = re.sub(r'<ul[^>]*>', '', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'</ul>', '', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'<ol[^>]*>', '', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'</ol>', '', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', markdown, flags=re.IGNORECASE | re.DOTALL)
    
    # Párrafos y saltos de línea
    markdown = re.sub(r'<p[^>]*>', '', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'</p>', '\n\n', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'<br[^>]*/?>', '\n', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'<div[^>]*>', '', markdown, flags=re.IGNORECASE)
    markdown = re.sub(r'</div>', '\n', markdown, flags=re.IGNORECASE)
    
    # Limpiar espacios en blanco excesivos
    markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
    markdown = markdown.strip()
    
    return markdown

@app.route('/api/check-apis', methods=['GET'])
def check_apis():
    """Endpoint para verificar qué APIs están configuradas"""
    apis_status = {
        'openai': bool(OPENAI_API_KEY),
        'google': bool(GOOGLE_API_KEY),
        'deepseek': bool(DEEPSEEK_API_KEY),
        'openrouter': bool(OPENROUTER_API_KEY)
    }
    return jsonify(apis_status)

@app.route('/api/list-saved-notes', methods=['GET'])
def list_saved_notes():
    """Endpoint para listar las notas guardadas en el servidor"""
    try:
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        
        if not os.path.exists(saved_notes_dir):
            return jsonify({"notes": [], "message": "Directorio saved_notes no existe"})
        
        # Listar todos los archivos .md en el directorio
        notes = []
        for filename in os.listdir(saved_notes_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(saved_notes_dir, filename)
                try:
                    # Obtener información del archivo
                    stat = os.stat(filepath)
                    note_id = None
                    meta_path = f"{filepath}.meta"
                    tags = []
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as meta_file:
                                meta = json.load(meta_file)
                            note_id = meta.get('id')
                            tags = [t.lower() for t in meta.get('tags', []) if isinstance(t, str)]
                        except Exception:
                            pass
                    notes.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "id": note_id,
                        "tags": tags
                    })
                except Exception as e:
                    print(f"Error al leer información del archivo {filename}: {e}")
        
        # Ordenar por fecha de modificación (más reciente primero)
        notes.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            "notes": notes,
            "count": len(notes),
            "directory": saved_notes_dir
        })
        
    except Exception as e:
        return jsonify({"error": f"Error al listar notas guardadas: {str(e)}"}), 500

@app.route('/api/cleanup-notes', methods=['POST'])
def cleanup_notes():
    """Endpoint para migrar notas existentes sin ID a la nueva estructura"""
    try:
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        if not os.path.exists(saved_notes_dir):
            return jsonify({"message": "No hay directorio de notas guardadas"}), 200
        
        migrated_count = 0
        for filename in os.listdir(saved_notes_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(saved_notes_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Si la nota no tiene ID, agregarle uno basado en el timestamp del archivo
                    if "*Nota ID:" not in content:
                        # Generar un ID único basado en el timestamp del archivo
                        stat = os.stat(filepath)
                        note_id = int(stat.st_mtime * 1000)  # Timestamp en ms
                        
                        # Agregar el ID al final del archivo
                        if content.endswith('\n'):
                            content += f"\n---\n*Nota ID: {note_id}*\n"
                        else:
                            content += f"\n\n---\n*Nota ID: {note_id}*\n"
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        migrated_count += 1
                
                except (IOError, UnicodeDecodeError) as e:
                    continue
        
        return jsonify({
            "success": True,
            "message": f"Migradas {migrated_count} notas a la nueva estructura",
            "migrated_count": migrated_count
        })
        
    except Exception as e:
        return jsonify({"error": f"Error al migrar notas: {str(e)}"}), 500

@app.route('/api/delete-note', methods=['POST'])
def delete_note():
    """Endpoint para eliminar una nota del servidor"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
        
        note_id = data.get('id')
        
        if not note_id:
            return jsonify({"error": "ID de nota requerido"}), 400
        
        # Buscar el archivo correspondiente al note_id
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        
        if not os.path.exists(saved_notes_dir):
            return jsonify({"error": "Directorio de notas no existe"}), 404
        
        # Buscar archivo con este note_id en metadatos
        deleted_file = None
        for filename in os.listdir(saved_notes_dir):
            if filename.endswith('.meta'):
                meta_path = os.path.join(saved_notes_dir, filename)
                try:
                    with open(meta_path, 'r', encoding='utf-8') as meta_file:
                        data = json.load(meta_file)
                    if str(data.get('id')) == str(note_id):
                        base = os.path.splitext(os.path.splitext(filename)[0])[0]
                        md_path = os.path.join(saved_notes_dir, f"{base}.md")
                        if os.path.exists(md_path):
                            os.remove(md_path)
                        os.remove(meta_path)
                        deleted_file = f"{base}.md"
                        break
                except Exception as e:
                    print(f"Error leyendo metadatos {filename}: {e}")
                    continue
        
        if deleted_file:
            return jsonify({
                "success": True,
                "message": "Nota eliminada correctamente del servidor",
                "filename": deleted_file
            })
        else:
            return jsonify({
                "success": True,
                "message": "Nota no encontrada en el servidor (puede no haberse guardado previamente)"
            })
        
    except Exception as e:
        return jsonify({"error": f"Error al eliminar la nota: {str(e)}"}), 500

@app.route('/api/list-notes', methods=['GET'])
def list_notes():
    """Endpoint para listar notas (guardadas y no guardadas) en el servidor"""
    try:
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        
        # Obtener todas las notas guardadas
        saved_notes = []
        if os.path.exists(saved_notes_dir):
            for filename in os.listdir(saved_notes_dir):
                if filename.endswith('.md'):
                    filepath = os.path.join(saved_notes_dir, filename)
                    try:
                        # Obtener información del archivo
                        stat = os.stat(filepath)
                        saved_notes.append({
                            "filename": filename,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                        })
                    except Exception as e:
                        print(f"Error al leer información del archivo {filename}: {e}")
        
        # Obtener notas no guardadas (siempre será una nota por defecto)
        unsaved_notes = [
            {
                "filename": "Nota temporal",
                "size": 0,
                "modified": datetime.now().isoformat(),
                "created": datetime.now().isoformat()
            }
        ]
        
        # Combinar y ordenar por fecha de modificación (más reciente primero)
        all_notes = saved_notes + unsaved_notes
        all_notes.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            "notes": all_notes,
            "count": len(all_notes),
            "directory": saved_notes_dir
        })
        
    except Exception as e:
        return jsonify({"error": f"Error al listar notas: {str(e)}"}), 500

@app.route('/api/download-all-notes', methods=['GET'])
def download_all_notes():
    """Descarga todas las notas guardadas como un archivo ZIP"""
    try:
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        if not os.path.exists(saved_notes_dir):
            return jsonify({"error": "No hay notas guardadas"}), 404

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in os.listdir(saved_notes_dir):
                if filename.endswith('.md') or filename.endswith('.meta'):
                    zipf.write(os.path.join(saved_notes_dir, filename), arcname=filename)
        mem_zip.seek(0)
        return send_file(mem_zip, as_attachment=True, download_name='all_notes.zip')
    except Exception as e:
        return jsonify({"error": f"Error al crear ZIP: {str(e)}"}), 500

@app.route('/api/upload-note', methods=['POST'])
def upload_note():
    """Sube una nota markdown al directorio saved_notes"""
    try:
        if 'note' not in request.files:
            return jsonify({"error": "No se recibió archivo"}), 400

        note_file = request.files['note']
        if note_file.filename == '':
            return jsonify({"error": "Tipo de archivo no válido"}), 400

        ext = os.path.splitext(note_file.filename)[1].lower()
        if ext not in ['.md', '.meta']:
            return jsonify({"error": "Tipo de archivo no válido"}), 400

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        os.makedirs(saved_notes_dir, exist_ok=True)
        filepath = os.path.join(saved_notes_dir, note_file.filename)
        overwritten = os.path.exists(filepath)
        note_file.save(filepath)

        return jsonify({"success": True, "filename": note_file.filename, "overwritten": overwritten})
    except Exception as e:
        return jsonify({"error": f"Error al subir nota: {str(e)}"}), 500

@app.route('/api/upload-model', methods=['POST'])
def upload_model():
    """Upload a whisper.cpp model file to the whisper-cpp-models directory"""
    try:
        if 'model' not in request.files:
            return jsonify({"error": "No se recibió archivo"}), 400

        model_file = request.files['model']
        if model_file.filename == '':
            return jsonify({"error": "Tipo de archivo no válido"}), 400

        ext = os.path.splitext(model_file.filename)[1].lower()
        if ext != '.bin':
            return jsonify({"error": "Tipo de archivo no válido"}), 400

        models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
        os.makedirs(models_dir, exist_ok=True)
        filepath = os.path.join(models_dir, model_file.filename)
        overwritten = os.path.exists(filepath)

        # Save incrementally to handle very large files without exhausting memory
        with open(filepath, 'wb') as f:
            for chunk in iter(lambda: model_file.stream.read(8192), b''):
                f.write(chunk)

        return jsonify({"success": True, "filename": model_file.filename, "overwritten": overwritten})
    except Exception as e:
        return jsonify({"error": f"Error al subir modelo: {str(e)}"}), 500

@app.route('/api/download-model', methods=['POST'])
def download_model():
    """Download a whisper.cpp model from the internet with progress via SSE"""
    data = request.get_json() or {}
    size = data.get('size')

    MODEL_URLS = {
        'tiny':   'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin',
        'base':   'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin',
        'small':  'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin',
        'medium': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin',
        'large':  'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large.bin',
    }

    if size not in MODEL_URLS:
        return jsonify({"error": "Modelo no válido"}), 400

    url = MODEL_URLS[size]

    def generate():
        try:
            models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
            os.makedirs(models_dir, exist_ok=True)
            filename = os.path.join(models_dir, os.path.basename(url))

            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total = int(r.headers.get('Content-Length', 0))
                downloaded = 0
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                progress = int(downloaded * 100 / total)
                                yield f"data: {json.dumps({'progress': progress})}\n\n"

            yield f"data: {json.dumps({'done': True, 'filename': os.path.basename(filename)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

@app.route('/api/download-sensevoice', methods=['POST'])
def download_sensevoice():
    """Download SenseVoice model from Hugging Face with progress via SSE"""
    try:
        def generate():
            global sensevoice_wrapper, SENSEVOICE_AVAILABLE
            try:
                # Import huggingface_hub here to avoid startup dependency
                try:
                    from huggingface_hub import HfApi, hf_hub_download
                    import subprocess
                    import sys
                except ImportError:
                    # Try to install huggingface_hub if not available
                    yield f"data: {json.dumps({'status': 'Installing huggingface_hub...'})}\n\n"
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
                        from huggingface_hub import HfApi, hf_hub_download
                    except Exception as install_error:
                        yield f"data: {json.dumps({'error': f'Failed to install huggingface_hub: {str(install_error)}'})}\n\n"
                        return
                
                # Note: FunASR will be installed on-demand when using SenseVoice for transcription
                # For now, we just download the model files
                yield f"data: {json.dumps({'status': 'FunASR will be installed when needed for transcription'})}\n\n"

                # Create models directory
                models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
                os.makedirs(models_dir, exist_ok=True)

                # Create SenseVoice specific directory
                sensevoice_dir = os.path.join(models_dir, 'SenseVoiceSmall')

                yield f"data: {json.dumps({'status': 'Starting SenseVoice Small download...'})}\n\n"
                yield f"data: {json.dumps({'progress': 0})}\n\n"

                # Download the model from Hugging Face
                repo_id = "FunAudioLLM/SenseVoiceSmall"
                yield f"data: {json.dumps({'status': f'Listing files in {repo_id}...'})}\n\n"

                api = HfApi()
                files = api.list_repo_files(repo_id=repo_id, repo_type="model")
                total_files = len(files)
                if total_files == 0:
                    yield f"data: {json.dumps({'error': 'No files found in repository'})}\n\n"
                    return

                yield f"data: {json.dumps({'status': f'Total files: {total_files}'})}\n\n"

                downloaded = 0
                for file in files:
                    hf_hub_download(repo_id=repo_id, filename=file, repo_type="model", local_dir=sensevoice_dir, local_dir_use_symlinks=False)
                    downloaded += 1
                    progress = int(downloaded * 100 / total_files)
                    yield f"data: {json.dumps({'progress': progress})}\n\n"

                yield f"data: {json.dumps({'status': 'Download completed successfully!'})}\n\n"
                yield f"data: {json.dumps({'progress': 100})}\n\n"
                yield f"data: {json.dumps({'done': True, 'filename': 'SenseVoiceSmall', 'path': sensevoice_dir})}\n\n"

                # Update availability and load model in background
                def _load_async():
                    global SENSEVOICE_AVAILABLE
                    SENSEVOICE_AVAILABLE = sensevoice_wrapper.is_available()
                    if SENSEVOICE_AVAILABLE:
                        sensevoice_wrapper.model_loaded = False
                        sensevoice_wrapper._load_model()

                threading.Thread(target=_load_async, daemon=True).start()
                
            except Exception as e:
                yield f"data: {json.dumps({'error': f'SenseVoice download failed: {str(e)}'})}\n\n"

        return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
        
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/api/get-note', methods=['GET'])
def get_note():
    """Devuelve el contenido de una nota especificada por ID o nombre de archivo"""
    try:
        note_id = request.args.get('id')
        filename = request.args.get('filename')

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes')
        if not os.path.exists(saved_notes_dir):
            return jsonify({"error": "Directorio de notas no existe"}), 404

        filepath = None
        if note_id:
            filepath = find_existing_note_file(saved_notes_dir, note_id)
        elif filename:
            candidate = os.path.join(saved_notes_dir, filename)
            if os.path.exists(candidate):
                filepath = candidate

        if not filepath:
            return jsonify({"error": "Nota no encontrada"}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        basename = os.path.basename(filepath)

        meta_path = f"{filepath}.meta"
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as meta_file:
                    meta = json.load(meta_file)
                note_id = meta.get('id', note_id)
            except Exception:
                pass

        return jsonify({"filename": basename, "id": note_id, "content": content})
    except Exception as e:
        return jsonify({"error": f"Error al leer nota: {str(e)}"}), 500

@app.route('/api/transcription-providers', methods=['GET'])
def get_transcription_providers():
    """Endpoint para obtener los proveedores de transcripción disponibles"""
    try:
        providers = []
        
        # Verificar OpenAI
        if OPENAI_API_KEY:
            providers.append({
                "id": "openai",
                "name": "OpenAI",
                "description": "Cloud-based transcription using OpenAI's API",
                "available": True,
                "models": ["whisper-1", "gpt-4o-mini-transcribe", "gpt-4o-transcribe"]
            })
        
        # Verificar whisper.cpp local
        if WHISPER_CPP_AVAILABLE and whisper_wrapper:
            models = whisper_wrapper.get_available_models()
            providers.append({
                "id": "local",
                "name": "Local Whisper",
                "description": "Local transcription using whisper.cpp",
                "available": True,
                "models": [model["name"] for model in models],
                "privacy": "Full privacy - no data leaves your device"
            })
        
        # Verificar SenseVoice
        if SENSEVOICE_AVAILABLE and sensevoice_wrapper:
            model_info = sensevoice_wrapper.get_model_info()
            providers.append({
                "id": "sensevoice",
                "name": "SenseVoice",
                "description": "Advanced multilingual speech recognition with emotion and event detection",
                "available": True,
                "models": ["SenseVoiceSmall"],
                "languages": [lang["code"] for lang in model_info["languages"]],
                "features": model_info["features"],
                "emotions": model_info["emotions"],
                "events": model_info["events"],
                "privacy": "Full privacy - no data leaves your device"
            })
        
        return jsonify({
            "providers": providers,
            "default": "openai" if OPENAI_API_KEY else ("sensevoice" if SENSEVOICE_AVAILABLE else ("local" if WHISPER_CPP_AVAILABLE else None))
        })
        
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('BACKEND_PORT', 8000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    # For large file uploads, we need to ensure proper configuration
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, request_handler=None)
