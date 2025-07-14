from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import os
import io
import zipfile
import re
import requests
import json
import time
from dotenv import load_dotenv
import tempfile
import base64
import re
from datetime import datetime
import shutil
from whisper_cpp_wrapper import WhisperCppWrapper
from sensevoice_wrapper import get_sensevoice_wrapper
import threading

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
LMSTUDIO_HOST = os.getenv('LMSTUDIO_HOST', '127.0.0.1')
LMSTUDIO_PORT = os.getenv('LMSTUDIO_PORT', '1234')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', '127.0.0.1')
OLLAMA_PORT = os.getenv('OLLAMA_PORT', '11434')
# Enable or disable multi-user support (default True)
MULTI_USER = os.getenv('MULTI_USER', 'true').lower() != 'false'
# File to persist LM Studio/Ollama configuration set by the admin
SERVER_CONFIG_FILE = os.path.join('data', 'server_config.json')

def load_server_config():
    """Load host/port settings from disk if available."""
    global LMSTUDIO_HOST, LMSTUDIO_PORT, OLLAMA_HOST, OLLAMA_PORT
    if os.path.exists(SERVER_CONFIG_FILE):
        try:
            with open(SERVER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            LMSTUDIO_HOST = data.get('lmstudio_host', LMSTUDIO_HOST)
            LMSTUDIO_PORT = data.get('lmstudio_port', LMSTUDIO_PORT)
            OLLAMA_HOST = data.get('ollama_host', OLLAMA_HOST)
            OLLAMA_PORT = data.get('ollama_port', OLLAMA_PORT)
        except Exception:
            pass

def save_server_config():
    """Persist current host/port settings to disk."""
    data = {
        'lmstudio_host': LMSTUDIO_HOST,
        'lmstudio_port': LMSTUDIO_PORT,
        'ollama_host': OLLAMA_HOST,
        'ollama_port': OLLAMA_PORT,
    }
    temp_dir = os.path.dirname(SERVER_CONFIG_FILE) or '.'
    fd, temp_path = tempfile.mkstemp(dir=temp_dir, prefix='srvcfg.', suffix='.tmp')
    os.close(fd)
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, SERVER_CONFIG_FILE)
    except Exception:
        try:
            shutil.move(temp_path, SERVER_CONFIG_FILE)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

# Load persisted config if present
load_server_config()
# Opcional: enviar las notas guardadas a un flujo de trabajo externo
WORKFLOW_WEBHOOK_URL = os.getenv('WORKFLOW_WEBHOOK_URL')
WORKFLOW_WEBHOOK_TOKEN = os.getenv('WORKFLOW_WEBHOOK_TOKEN')
WORKFLOW_WEBHOOK_USER = os.getenv('WORKFLOW_WEBHOOK_USER')

# ---------- User management with PostgreSQL ---------
SAVE_LOCK = threading.Lock()
SESSIONS = {}
ALL_TRANSCRIPTION_PROVIDERS = ["openai", "local", "sensevoice"]
ALL_POSTPROCESS_PROVIDERS = ["openai", "google", "openrouter", "lmstudio", "ollama"]

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from argon2.low_level import Type
from db import (
    init_db,
    migrate_json,
    get_user,
    list_users as db_list_users,
    create_user as db_create_user,
    update_password as db_update_password,
    update_user_providers as db_update_user_providers,
    delete_user as db_delete_user,
)

HASHER = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32, type=Type.ID)

init_db()
migrate_json(hasher=HASHER)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD environment variable not set")

def ensure_admin_user():
    if not get_user('admin'):
        db_create_user(
            'admin',
            HASHER.hash(ADMIN_PASSWORD),
            True,
            ALL_TRANSCRIPTION_PROVIDERS,
            ALL_POSTPROCESS_PROVIDERS,
        )

ensure_admin_user()

def get_user_providers(username):
    user = get_user(username)
    if not user:
        return [], []
    if username == 'admin':
        return ALL_TRANSCRIPTION_PROVIDERS, ALL_POSTPROCESS_PROVIDERS
    return user.get('transcription_providers', []), user.get('postprocess_providers', [])


def migrate_notes_to_admin_folder():
    """Move existing notes in saved_notes/ to saved_notes/admin"""
    root_dir = os.path.join(os.getcwd(), 'saved_notes')
    if not os.path.isdir(root_dir):
        return

    admin_dir = os.path.join(root_dir, 'admin')
    moved = 0

    for fname in os.listdir(root_dir):
        path = os.path.join(root_dir, fname)
        if os.path.isfile(path) and (fname.endswith('.md') or fname.endswith('.meta')):
            os.makedirs(admin_dir, exist_ok=True)
            shutil.move(path, os.path.join(admin_dir, fname))
            moved += 1

    if moved:
        print(f"Migrated {moved} notes to {admin_dir}")


def parse_note_id_from_md(path):
    """Try to extract a note ID from the markdown file"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r"\*Nota ID:\s*(\d+)\*", content)
        if not match:
            match = re.search(r"\*Note ID:\s*(\d+)\*", content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def generate_note_id_from_filename(filename: str) -> str:
    """Return a stable note ID derived from the filename"""
    base = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()


def create_missing_meta_files():
    """Ensure every note has a corresponding .meta file with an ID"""
    root_dir = os.path.join(os.getcwd(), 'saved_notes')
    if not os.path.isdir(root_dir):
        return 0

    created = 0
    for user in os.listdir(root_dir):
        user_dir = os.path.join(root_dir, user)
        if not os.path.isdir(user_dir):
            continue
        for fname in os.listdir(user_dir):
            if not fname.endswith('.md'):
                continue
            md_path = os.path.join(user_dir, fname)
            meta_path = f"{md_path}.meta"
            if os.path.exists(meta_path):
                continue
            note_id = parse_note_id_from_md(md_path)
            if not note_id:
                note_id = generate_note_id_from_filename(fname)
            stat = os.stat(md_path)
            metadata = {
                "id": note_id,
                "title": os.path.splitext(fname)[0],
                "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "tags": []
            }
            try:
                with open(meta_path, 'w', encoding='utf-8') as mf:
                    json.dump(metadata, mf, ensure_ascii=False, indent=2)
                created += 1
            except Exception as e:
                print(f"Error creating meta for {md_path}: {e}")
    if created:
        print(f"Created {created} metadata files")
    return created


migrate_notes_to_admin_folder()
create_missing_meta_files()

def get_current_username():
    if not MULTI_USER:
        return 'admin'
    token = request.headers.get('Authorization')
    if not token:
        return None
    return SESSIONS.get(token)

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
    print("SenseVoice wrapper initialized")
    # Check initial availability (for logging purposes)
    initial_sensevoice_available = sensevoice_wrapper.is_available()
    print(f"SenseVoice initially available: {initial_sensevoice_available}")
    # Note: We'll check availability dynamically instead of caching it
except Exception as e:
    print(f"Error initializing SenseVoice wrapper: {e}")
    sensevoice_wrapper = None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el backend está funcionando"""
    return jsonify({"status": "ok", "message": "Backend funcionando correctamente"})

# --- Authentication and user management endpoints ---

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    user = get_user(username)
    if not user:
        return jsonify({"success": False}), 401
    try:
        HASHER.verify(user['password'], password)
    except argon2_exceptions.VerifyMismatchError:
        return jsonify({"success": False}), 401
    if HASHER.check_needs_rehash(user['password']):
        db_update_password(username, HASHER.hash(password))
    token = base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
    SESSIONS[token] = username
    tp, pp = get_user_providers(username)
    return jsonify({
        "success": True,
        "token": token,
        "is_admin": user.get('is_admin', False),
        "transcription_providers": tp,
        "postprocess_providers": pp,
    })


@app.route('/api/logout', methods=['POST'])
def logout_user():
    token = request.headers.get('Authorization')
    if token in SESSIONS:
        SESSIONS.pop(token, None)
    return jsonify({"success": True})


@app.route('/api/session-info', methods=['GET'])
def session_info():
    """Return information about the current session if the token is valid"""
    if not MULTI_USER:
        username = 'admin'
    else:
        token = request.headers.get('Authorization')
        username = SESSIONS.get(token)
        if not username:
            return jsonify({"authenticated": False}), 401
    user = get_user(username) or {}
    tp, pp = get_user_providers(username)
    return jsonify({
        "authenticated": True,
        "username": username,
        "is_admin": user.get('is_admin', False),
        "transcription_providers": tp,
        "postprocess_providers": pp,
    })


@app.route('/api/change-password', methods=['POST'])
def change_password():
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    current = data.get('current_password')
    new_password = data.get('new_password')
    if not current or not new_password:
        return jsonify({"error": "Password required"}), 400
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    try:
        HASHER.verify(user['password'], current)
    except argon2_exceptions.VerifyMismatchError:
        return jsonify({"error": "Current password incorrect"}), 400
    new_hash = HASHER.hash(new_password)
    db_update_password(username, new_hash)
    return jsonify({"success": True})


@app.route('/api/create-user', methods=['POST'])
def create_user():
    admin = get_current_username()
    admin_info = get_user(admin)
    if not admin or not admin_info or not admin_info.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if get_user(username) or username == 'admin':
        return jsonify({"error": "User exists"}), 400
    db_create_user(
        username,
        HASHER.hash(password),
        False,
        data.get('transcription_providers', []),
        data.get('postprocess_providers', []),
    )
    return jsonify({"success": True})


@app.route('/api/list-users', methods=['GET'])
def list_users():
    admin = get_current_username()
    admin_info = get_user(admin)
    if not admin or not admin_info or not admin_info.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"users": db_list_users()})


@app.route('/api/update-user-providers', methods=['POST'])
def update_user_providers():
    admin = get_current_username()
    admin_info = get_user(admin)
    if not admin or not admin_info or not admin_info.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    username = data.get('username')
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if username == 'admin':
        return jsonify({"error": "Cannot modify admin"}), 400
    db_update_user_providers(
        username,
        data.get('transcription_providers', user.get('transcription_providers', [])),
        data.get('postprocess_providers', user.get('postprocess_providers', [])),
    )
    return jsonify({"success": True})


@app.route('/api/delete-user', methods=['POST'])
def delete_user():
    """Remove a non-admin user and delete their notes folder"""
    admin = get_current_username()
    admin_info = get_user(admin)
    if not admin or not admin_info or not admin_info.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    username = data.get('username')
    if not username or not get_user(username):
        return jsonify({"error": "User not found"}), 404
    if username == 'admin':
        return jsonify({"error": "Cannot delete admin"}), 400
    db_delete_user(username)

    user_dir = os.path.join(os.getcwd(), 'saved_notes', username)
    try:
        shutil.rmtree(user_dir)
    except FileNotFoundError:
        pass

    return jsonify({"success": True})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Endpoint para transcribir audio usando OpenAI o whisper.cpp local"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        # Obtener el archivo de audio del request
        if 'audio' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Archivo de audio vacío"}), 400
        
        # Obtener parámetros del request
        language = request.form.get('language', None)  # None = detección automática
        provider = request.form.get('provider', 'openai')  # openai o local

        tp, _ = get_user_providers(username)
        if tp and provider not in tp:
            return jsonify({"error": "Transcription provider not allowed"}), 403
        model_name = request.form.get('model')
        
        # Verificar disponibilidad del proveedor
        if provider == 'local':
            if not WHISPER_CPP_AVAILABLE:
                return jsonify({"error": "Whisper.cpp local no está disponible"}), 500

            if not model_name:
                return jsonify({"error": "Model not specified"}), 400

            audio_bytes = audio_file.read()

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
                    "model": result.get('model')
                })
            else:
                return jsonify({"error": f"Error en transcripción local: {result.get('error', 'Unknown error')}"}), 500
        
        elif provider == 'sensevoice':
            # Check SenseVoice availability dynamically
            sensevoice_available = sensevoice_wrapper and sensevoice_wrapper.is_available()
            if not sensevoice_available:
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

            if not model_name:
                return jsonify({"error": "Model not specified"}), 400

            # Preparar la petición a OpenAI
            model_to_use = model_name
            files = {
                'file': (audio_file.filename, audio_file.stream, audio_file.content_type),
                'model': (None, model_to_use)
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
                    "model": model_to_use
                })
            else:
                return jsonify({"error": "Error en la transcripción"}), response.status_code
            
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/api/improve-text', methods=['POST'])
def improve_text():
    """Endpoint para mejorar texto usando OpenAI o Google AI"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "Faltan parámetros requeridos"}), 400

        # Chat assistant support
        if 'messages' in data:
            provider = data.get('provider', 'openai')
            _, pp = get_user_providers(username)
            if pp and provider not in pp:
                return jsonify({"error": "Post-process provider not allowed"}), 403
            stream = data.get('stream', False)
            model = data.get('model')
            note = data.get('note', '')
            messages = data['messages']
            if note:
                messages = [{'role': 'system', 'content': note}] + messages

            if not model:
                return jsonify({"error": "Model not specified"}), 400

            if stream:
                if provider == 'openai':
                    return chat_openai_stream(messages, model)
                elif provider == 'google':
                    return chat_google_stream(messages, model)
                elif provider == 'openrouter':
                    return chat_openrouter_stream(messages, model)
                elif provider == 'lmstudio':
                    host = data.get('host', LMSTUDIO_HOST)
                    port = data.get('port', LMSTUDIO_PORT)
                    return chat_lmstudio_stream(messages, model, host, port)
                elif provider == 'ollama':
                    host = data.get('host', OLLAMA_HOST)
                    port = data.get('port', OLLAMA_PORT)
                    return chat_ollama_stream(messages, model, host, port)
                else:
                    return jsonify({"error": "Proveedor no soportado para streaming"}), 400

            else:
                return jsonify({"error": "Non-streaming chat not supported"}), 400

        if 'text' not in data or 'improvement_type' not in data:
            return jsonify({"error": "Faltan parámetros requeridos"}), 400
        
        text = data['text']
        improvement_type = data['improvement_type']
        provider = data.get('provider', 'openai')  # openai o google

        _, pp = get_user_providers(username)
        if pp and provider not in pp:
            return jsonify({"error": "Post-process provider not allowed"}), 403
        stream = data.get('stream', False)  # Nuevo parámetro para streaming
        custom_prompt = data.get('custom_prompt')  # Nuevo parámetro para prompts personalizados
        
        if stream:
            if provider == 'openai':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_openai_stream(text, improvement_type, model, custom_prompt)
            elif provider == 'google':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_google_stream(text, improvement_type, model, custom_prompt)
            elif provider == 'openrouter':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_openrouter_stream(text, improvement_type, model, custom_prompt)
            elif provider == 'lmstudio':
                model = data.get('model')
                host = data.get('host', LMSTUDIO_HOST)
                port = data.get('port', LMSTUDIO_PORT)
                return improve_text_lmstudio_stream(text, improvement_type, model, host, port, custom_prompt)
            elif provider == 'ollama':
                model = data.get('model')
                host = data.get('host', OLLAMA_HOST)
                port = data.get('port', OLLAMA_PORT)
                return improve_text_ollama_stream(text, improvement_type, model, host, port, custom_prompt)
            else:
                return jsonify({"error": "Proveedor no soportado para streaming"}), 400
        else:
            if provider == 'openai':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_openai(text, improvement_type, model, custom_prompt)
            elif provider == 'google':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_google(text, improvement_type, model, custom_prompt)
            elif provider == 'openrouter':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_openrouter(text, improvement_type, model, custom_prompt)
            elif provider == 'lmstudio':
                model = data.get('model')
                host = data.get('host', LMSTUDIO_HOST)
                port = data.get('port', LMSTUDIO_PORT)
                return improve_text_lmstudio(text, improvement_type, model, host, port, custom_prompt)
            elif provider == 'ollama':
                model = data.get('model')
                host = data.get('host', OLLAMA_HOST)
                port = data.get('port', OLLAMA_PORT)
                return improve_text_ollama(text, improvement_type, model, host, port, custom_prompt)
            else:
                return jsonify({"error": "Proveedor no soportado"}), 400
            
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def improve_text_openai(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando OpenAI"""
    if not OPENAI_API_KEY:
        return jsonify({"error": "API key de OpenAI no configurada"}), 500

    if not model:
        return jsonify({"error": "Model not specified"}), 400
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
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

def improve_text_google(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando Google AI (Gemini)"""
    if not GOOGLE_API_KEY:
        return jsonify({"error": "API key de Google no configurada"}), 500

    if not model:
        return jsonify({"error": "Model not specified"}), 400
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")
    
    # Nueva URL según la documentación oficial de Gemini
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    
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

def improve_text_openai_stream(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando OpenAI con streaming"""
    if not OPENAI_API_KEY:
        return jsonify({"error": "API key de OpenAI no configurada"}), 500

    if not model:
        return jsonify({"error": "Model not specified"}), 400
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
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

def improve_text_google_stream(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando Google AI con streaming (simulado)"""
    if not GOOGLE_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de Google no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    if not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'Model not specified'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
    
    # Google AI no soporta streaming nativamente, así que simularemos
    # Primero obtenemos la respuesta completa
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    
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

def improve_text_openrouter(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando OpenRouter"""
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "API key de OpenRouter no configurada"}), 500

    if not model:
        return jsonify({"error": "Model not specified"}), 400
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")
    
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

def improve_text_openrouter_stream(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando OpenRouter con streaming"""
    if not OPENROUTER_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de OpenRouter no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    if not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'Model not specified'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
    
    # Si se proporciona un prompt personalizado, usarlo directamente
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        # Definir prompts según el tipo de mejora (solo para estilos predeterminados)
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")
    
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

def improve_text_lmstudio(text, improvement_type, model, host, port, custom_prompt=None):
    """Mejorar texto usando LM Studio local"""
    if not host or not port or not model:
        return jsonify({"error": "LM Studio host, port and model required"}), 400

    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }

        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")

    url = f"http://{host}:{port}/v1/chat/completions"
    headers = { 'Content-Type': 'application/json' }
    payload = {
        'model': model,
        'messages': [{ 'role': 'user', 'content': prompt }],
        'max_tokens': 1000,
        'temperature': 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            improved_text = result['choices'][0]['message']['content']
            return jsonify({"improved_text": improved_text})
        else:
            return jsonify({"error": f"LM Studio error {response.status_code}"}), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": f"Error de conexión con LM Studio: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route('/api/ollama/models', methods=['GET'])
def get_ollama_models():
    """Query Ollama for available models"""
    host = request.args.get('host', OLLAMA_HOST)
    port = request.args.get('port', OLLAMA_PORT)

    try:
        url = f"http://{host}:{port}/api/tags"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return jsonify({"error": f"Ollama error {response.status_code}"}), response.status_code
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": f"Error de conexión con Ollama: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def improve_text_lmstudio_stream(text, improvement_type, model, host, port, custom_prompt=None):
    """Mejorar texto usando LM Studio con streaming"""
    if not host or not port or not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'LM Studio host, port and model required'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }

        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")

    url = f"http://{host}:{port}/v1/chat/completions"
    headers = { 'Content-Type': 'application/json' }
    payload = {
        'model': model,
        'messages': [{ 'role': 'user', 'content': prompt }],
        'max_tokens': 1000,
        'temperature': 0.7,
        'stream': True
    }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'LM Studio error {response.status_code}'})}\n\n"
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
            yield f"data: {json.dumps({'error': f'Error de conexión con LM Studio: {str(e)}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error interno: {str(e)}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def improve_text_ollama(text, improvement_type, model, host, port, custom_prompt=None):
    """Mejorar texto usando Ollama local"""
    if not host or not port or not model:
        return jsonify({"error": "Ollama host, port and model required"}), 400

    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }

        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")

    url = f"http://{host}:{port}/api/chat"
    headers = { 'Content-Type': 'application/json' }
    payload = {
        'model': model,
        'messages': [{ 'role': 'user', 'content': prompt }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            improved_text = result.get('message', {}).get('content', '')
            return jsonify({"improved_text": improved_text})
        else:
            return jsonify({"error": f"Ollama error {response.status_code}"}), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": f"Error de conexión con Ollama: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def improve_text_ollama_stream(text, improvement_type, model, host, port, custom_prompt=None):
    """Mejorar texto usando Ollama con streaming"""
    if not host or not port or not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'Ollama host, port and model required'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}"
        }

        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")

    url = f"http://{host}:{port}/api/chat"
    headers = { 'Content-Type': 'application/json' }
    payload = {
        'model': model,
        'messages': [{ 'role': 'user', 'content': prompt }],
        'stream': True
    }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'Ollama error {response.status_code}'})}\n\n"
                return
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data.get('message') and data['message'].get('content'):
                            content = data['message']['content']
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        if data.get('done'):
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.RequestException as e:
            yield f"data: {json.dumps({'error': f'Error de conexión con Ollama: {str(e)}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error interno: {str(e)}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def chat_openai_stream(messages, model):
    if not OPENAI_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de OpenAI no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    url = 'https://api.openai.com/v1/chat/completions'
    headers = { 'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json' }
    payload = { 'model': model, 'messages': messages, 'stream': True }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': 'OpenAI error'})}\n\n"
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
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield f"data: {json.dumps({'content': delta['content']})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def chat_google_stream(messages, model):
    if not GOOGLE_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de Google no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    headers = { 'Content-Type': 'application/json' }
    payload = { 'contents': [ { 'role': m['role'], 'parts': [ { 'text': m['content'] } ] } for m in messages ] }

    def generate():
        try:
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                yield f"data: {json.dumps({'error': f'Google error {resp.status_code}'})}\n\n"
                return
            result = resp.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            for word in text.split(' '):
                yield f"data: {json.dumps({'content': word if word.startswith(' ') else ' ' + word})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def chat_openrouter_stream(messages, model):
    if not OPENROUTER_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de OpenRouter no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://note-transcribe-ai.local',
        'X-Title': 'Note Transcribe AI'
    }
    payload = { 'model': model, 'messages': messages, 'stream': True }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'OpenRouter error {response.status_code}'})}\n\n"
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
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield f"data: {json.dumps({'content': delta['content']})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def chat_lmstudio_stream(messages, model, host, port):
    if not host or not port or not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'LM Studio host, port and model required'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    url = f"http://{host}:{port}/v1/chat/completions"
    headers = { 'Content-Type': 'application/json' }
    payload = { 'model': model, 'messages': messages, 'stream': True }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'LM Studio error {response.status_code}'})}\n\n"
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
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield f"data: {json.dumps({'content': delta['content']})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def chat_ollama_stream(messages, model, host, port):
    if not host or not port or not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'Ollama host, port and model required'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    url = f"http://{host}:{port}/api/chat"
    headers = { 'Content-Type': 'application/json' }
    payload = { 'model': model, 'messages': messages, 'stream': True }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'Ollama error {response.status_code}'})}\n\n"
                return
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data.get('message') and data['message'].get('content'):
                            yield f"data: {json.dumps({'content': data['message']['content']})}\n\n"
                        if data.get('done'):
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

@app.route('/api/transcribe-gpt4o', methods=['POST'])
def transcribe_audio_gpt4o():
    """Endpoint para transcribir audio usando GPT-4o transcription models con soporte para streaming"""
    try:
        print(f"[DEBUG] Iniciando transcripción GPT-4o...")
        
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        tp, _ = get_user_providers(username)
        if tp and 'openai' not in tp:
            return jsonify({"error": "Transcription provider not allowed"}), 403

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
        model = request.form.get('model')
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
        
        if not model:
            print(f"[ERROR] Modelo no especificado")
            return jsonify({"error": "Model not specified"}), 400

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
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
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
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)

        with SAVE_LOCK:
            os.makedirs(saved_notes_dir, exist_ok=True)

            # Generar nombre de archivo seguro basado en el título
            if not title:
                title = "Untitled Note"

            safe_filename = generate_safe_filename(title)
            new_filename = f"{safe_filename}.md"
            new_filepath = os.path.join(saved_notes_dir, new_filename)

            # Buscar archivo existente para esta nota
            existing_filepath = find_existing_note_file(saved_notes_dir, note_id)

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
                        if os.path.exists(new_meta):
                            os.remove(new_meta)
                        os.rename(old_meta, new_meta)
                except OSError as e:
                    return jsonify({"error": f"Error al renombrar archivo: {str(e)}"}), 500
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

        # Enviar la nota al webhook configurado, si está disponible
        if WORKFLOW_WEBHOOK_URL:
            headers = {"Content-Type": "application/json"}
            if WORKFLOW_WEBHOOK_TOKEN:
                headers["Authorization"] = f"Bearer {WORKFLOW_WEBHOOK_TOKEN}"
            try:
                requests.post(
                    WORKFLOW_WEBHOOK_URL,
                    json={
                        "id": note_id,
                        "title": title,
                        "content": content,
                        "tags": tags,
                        "user": WORKFLOW_WEBHOOK_USER or username,
                    },
                    headers=headers,
                    timeout=5,
                )
            except Exception as e:
                print(f"Webhook error: {e}")

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


@app.route('/api/app-config', methods=['GET'])
def app_config():
    """Return basic frontend configuration"""
    return jsonify({
        "multi_user": MULTI_USER
    })


@app.route('/api/default-provider-config', methods=['GET'])
def default_provider_config():
    """Return default host/port values for local providers"""
    return jsonify({
        "lmstudio_host": LMSTUDIO_HOST,
        "lmstudio_port": LMSTUDIO_PORT,
        "ollama_host": OLLAMA_HOST,
        "ollama_port": OLLAMA_PORT,
    })

@app.route('/api/update-provider-config', methods=['POST'])
def update_provider_config():
    """Allow admin users to update LM Studio/Ollama host and port."""
    admin = get_current_username()
    admin_info = get_user(admin)
    if not admin or not admin_info or not admin_info.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    global LMSTUDIO_HOST, LMSTUDIO_PORT, OLLAMA_HOST, OLLAMA_PORT
    LMSTUDIO_HOST = data.get('lmstudio_host', LMSTUDIO_HOST)
    LMSTUDIO_PORT = data.get('lmstudio_port', LMSTUDIO_PORT)
    OLLAMA_HOST = data.get('ollama_host', OLLAMA_HOST)
    OLLAMA_PORT = data.get('ollama_port', OLLAMA_PORT)
    save_server_config()
    return jsonify({"success": True})

@app.route('/api/list-saved-notes', methods=['GET'])
def list_saved_notes():
    """Endpoint para listar las notas guardadas en el servidor"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        if not os.path.exists(saved_notes_dir):
            return jsonify({"notes": [], "message": "Directorio saved_notes no existe"})

        # Ensure missing metadata is created for this user's notes
        for fname in os.listdir(saved_notes_dir):
            if fname.endswith('.md'):
                meta = f"{os.path.join(saved_notes_dir, fname)}.meta"
                if not os.path.exists(meta):
                    note_id = parse_note_id_from_md(os.path.join(saved_notes_dir, fname))
                    if not note_id:
                        note_id = generate_note_id_from_filename(fname)
                    stat = os.stat(os.path.join(saved_notes_dir, fname))
                    meta_data = {
                        "id": note_id,
                        "title": os.path.splitext(fname)[0],
                        "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "tags": []
                    }
                    try:
                        with open(meta, 'w', encoding='utf-8') as mf:
                            json.dump(meta_data, mf, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
        
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
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        if not os.path.exists(saved_notes_dir):
            return jsonify({"message": "No hay directorio de notas guardadas"}), 200
        
        created = 0
        for filename in os.listdir(saved_notes_dir):
            if not filename.endswith('.md'):
                continue
            md_path = os.path.join(saved_notes_dir, filename)
            meta_path = f"{md_path}.meta"
            if os.path.exists(meta_path):
                continue
            note_id = parse_note_id_from_md(md_path)
            if not note_id:
                note_id = generate_note_id_from_filename(filename)
            stat = os.stat(md_path)
            metadata = {
                "id": note_id,
                "title": os.path.splitext(filename)[0],
                "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "tags": []
            }
            try:
                with open(meta_path, 'w', encoding='utf-8') as meta_file:
                    json.dump(metadata, meta_file, ensure_ascii=False, indent=2)
                created += 1
            except Exception:
                continue

        return jsonify({
            "success": True,
            "message": f"Metadatos creados: {created}",
            "migrated_count": created
        })
        
    except Exception as e:
        return jsonify({"error": f"Error al migrar notas: {str(e)}"}), 500

@app.route('/api/delete-note', methods=['POST'])
def delete_note():
    """Endpoint para eliminar una nota del servidor"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
        
        note_id = data.get('id')
        
        if not note_id:
            return jsonify({"error": "ID de nota requerido"}), 400
        
        # Buscar el archivo correspondiente al note_id
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
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
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
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
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
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
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        if 'note' not in request.files:
            return jsonify({"error": "No se recibió archivo"}), 400

        note_file = request.files['note']
        if note_file.filename == '':
            return jsonify({"error": "Tipo de archivo no válido"}), 400

        ext = os.path.splitext(note_file.filename)[1].lower()
        if ext not in ['.md', '.meta']:
            return jsonify({"error": "Tipo de archivo no válido"}), 400

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
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
        username = get_current_username()
        if username != 'admin':
            return jsonify({"error": "Unauthorized"}), 403
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
    username = get_current_username()
    if username != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
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
        username = get_current_username()
        if username != 'admin':
            return jsonify({"error": "Unauthorized"}), 403
        def generate():
            try:
                # Import huggingface_hub here to avoid startup dependency
                try:
                    from huggingface_hub import snapshot_download
                    import subprocess
                    import sys
                except ImportError:
                    # Try to install huggingface_hub if not available
                    yield f"data: {json.dumps({'status': 'Installing huggingface_hub...'})}\n\n"
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
                        from huggingface_hub import snapshot_download
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
                yield f"data: {json.dumps({'progress': 5})}\n\n"
                
                # Download the model from Hugging Face in two phases
                repo_id = "FunAudioLLM/SenseVoiceSmall"
                yield f"data: {json.dumps({'status': f'Preparing download from {repo_id}...'})}\n\n"
                yield f"data: {json.dumps({'progress': 10})}\n\n"
                
                # Phase 1: Download model.pt with progress tracking
                yield f"data: {json.dumps({'status': 'Downloading model.pt (936 MB)...'})}\n\n"
                yield f"data: {json.dumps({'progress': 15})}\n\n"
                
                try:
                    import requests
                    from urllib.parse import urljoin
                    
                    # Direct download of model.pt with progress
                    model_url = f"https://huggingface.co/{repo_id}/resolve/main/model.pt"
                    model_path = os.path.join(sensevoice_dir, 'model.pt')
                    
                    # Create directory if it doesn't exist
                    os.makedirs(sensevoice_dir, exist_ok=True)
                    
                    # Set headers for better compatibility
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; WhisPad/1.0)',
                        'Accept': 'application/octet-stream, */*',
                    }
                    
                    # Download with progress tracking
                    response = requests.get(model_url, stream=True, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    yield f"data: {json.dumps({'status': f'Starting download of model.pt ({total_size // (1024*1024)} MB)...'})}\n\n"
                    
                    with open(model_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                if total_size > 0:
                                    # Progress from 15% to 70% for model.pt download
                                    progress = 15 + int((downloaded / total_size) * 55)
                                    mb_downloaded = downloaded // (1024*1024)
                                    mb_total = total_size // (1024*1024)
                                    yield f"data: {json.dumps({'progress': progress, 'status': f'Downloading model.pt: {mb_downloaded}/{mb_total} MB ({progress-15:.1f}%)'})}\n\n"
                                else:
                                    # Fallback if content-length is not available
                                    mb_downloaded = downloaded // (1024*1024)
                                    yield f"data: {json.dumps({'status': f'Downloading model.pt: {mb_downloaded} MB...'})}\n\n"
                    
                    # Verify the downloaded file
                    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
                        final_size = os.path.getsize(model_path) // (1024*1024)
                        yield f"data: {json.dumps({'progress': 70, 'status': f'model.pt downloaded successfully! ({final_size} MB)'})}\n\n"
                    else:
                        raise Exception("Downloaded file is empty or doesn't exist")
                    
                except Exception as model_download_error:
                    yield f"data: {json.dumps({'status': f'HTTP download failed: {str(model_download_error)}, trying git-lfs...'})}\n\n"
                    
                    # Fallback: try using git clone with LFS
                    try:
                        import subprocess
                        import shutil
                        
                        # Remove any partial download
                        if os.path.exists(model_path):
                            os.remove(model_path)
                        if os.path.exists(sensevoice_dir):
                            shutil.rmtree(sensevoice_dir)
                        
                        # Clone with git-lfs
                        clone_url = f"https://huggingface.co/{repo_id}.git"
                        yield f"data: {json.dumps({'progress': 30, 'status': 'Cloning repository with git-lfs...'})}\n\n"
                        
                        result = subprocess.run([
                            'git', 'clone', '--progress', clone_url, sensevoice_dir
                        ], capture_output=True, text=True, timeout=600)  # 10 minutes timeout
                        
                        if result.returncode == 0:
                            yield f"data: {json.dumps({'progress': 70, 'status': 'Repository cloned successfully!'})}\n\n"
                        else:
                            raise Exception(f"Git clone failed: {result.stderr}")
                        
                    except Exception as git_error:
                        yield f"data: {json.dumps({'error': f'All download methods failed. HTTP: {str(model_download_error)}, Git: {str(git_error)}'})}\n\n"
                        return
                
                # Phase 2: Download remaining files using huggingface_hub
                yield f"data: {json.dumps({'progress': 75, 'status': 'Downloading remaining model files...'})}\n\n"
                
                try:
                    # Download all files except model.pt (which we already have)
                    snapshot_download(
                        repo_id=repo_id,
                        local_dir=sensevoice_dir,
                        repo_type="model",
                        local_files_only=False,
                        allow_patterns=None,
                        ignore_patterns=["model.pt"]  # Skip model.pt since we already downloaded it
                    )
                    yield f"data: {json.dumps({'progress': 90})}\n\n"
                except Exception as remaining_download_error:
                    yield f"data: {json.dumps({'error': f'Failed to download remaining files: {str(remaining_download_error)}'})}\n\n"
                    return
                
                # Verify that all required files were downloaded
                yield f"data: {json.dumps({'status': 'Verifying downloaded files...'})}\n\n"
                required_files = ['config.yaml', 'model.pt']
                missing_files = []
                verification_info = []
                
                for file in required_files:
                    file_path = os.path.join(sensevoice_dir, file)
                    if not os.path.exists(file_path):
                        missing_files.append(file)
                    else:
                        file_size = os.path.getsize(file_path)
                        size_mb = file_size / (1024 * 1024)
                        verification_info.append(f'{file}: {size_mb:.1f} MB')
                
                if missing_files:
                    yield f"data: {json.dumps({'error': f'Download incomplete: missing files {missing_files}'})}\n\n"
                    return
                
                # Success message with file info
                verification_msg = f"All files verified: {', '.join(verification_info)}"
                yield f"data: {json.dumps({'status': verification_msg})}\n\n"
                
                yield f"data: {json.dumps({'progress': 80})}\n\n"
                yield f"data: {json.dumps({'status': 'Download completed successfully!'})}\n\n"
                yield f"data: {json.dumps({'progress': 100})}\n\n"
                yield f"data: {json.dumps({'done': True, 'filename': 'SenseVoiceSmall', 'path': sensevoice_dir})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': f'SenseVoice download failed: {str(e)}'})}\n\n"

        return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
        
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/api/refresh-providers', methods=['POST'])
def refresh_providers():
    """Force refresh of transcription providers availability"""
    try:
        # This endpoint forces a fresh check of all providers
        # The actual refresh happens automatically when /api/transcription-providers is called
        # since we now check availability dynamically
        
        # Log current status for debugging
        whisper_available = WHISPER_CPP_AVAILABLE and whisper_wrapper
        sensevoice_available = sensevoice_wrapper and sensevoice_wrapper.is_available()
        
        print(f"Provider refresh requested:")
        print(f"  - Whisper.cpp available: {whisper_available}")
        print(f"  - SenseVoice available: {sensevoice_available}")
        
        return jsonify({
            "success": True,
            "message": "Providers refreshed successfully",
            "providers": {
                "whisper_cpp": whisper_available,
                "sensevoice": sensevoice_available
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Error refreshing providers: {str(e)}"}), 500

# New endpoints to manage downloaded whisper.cpp models

@app.route('/api/list-models', methods=['GET'])
def list_models():
    """List downloaded whisper.cpp models"""
    try:
        models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
        if not os.path.exists(models_dir):
            return jsonify({"models": [], "count": 0})

        models = []
        for entry in os.listdir(models_dir):
            path = os.path.join(models_dir, entry)
            size = 0
            if os.path.isfile(path):
                size = os.path.getsize(path)
            elif os.path.isdir(path):
                for root_dir, _, files in os.walk(path):
                    for f in files:
                        try:
                            size += os.path.getsize(os.path.join(root_dir, f))
                        except OSError:
                            pass
            models.append({
                "name": entry,
                "size": size,
                "is_dir": os.path.isdir(path)
            })

        return jsonify({"models": models, "count": len(models)})
    except Exception as e:
        return jsonify({"error": f"Error listing models: {str(e)}"}), 500


@app.route('/api/lmstudio/models', methods=['GET'])
def get_lmstudio_models():
    """Query LM Studio for available models"""
    host = request.args.get('host', LMSTUDIO_HOST)
    port = request.args.get('port', LMSTUDIO_PORT)

    try:
        url = f"http://{host}:{port}/v1/models"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return jsonify({"error": f"LM Studio error {response.status_code}"}), response.status_code
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": f"Error de conexión con LM Studio: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route('/api/delete-model', methods=['POST'])
def delete_model():
    """Delete a downloaded whisper.cpp model"""
    try:
        data = request.get_json() or {}
        name = data.get('name')
        if not name:
            return jsonify({"error": "Nombre de modelo requerido"}), 400

        models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
        target = os.path.join(models_dir, os.path.basename(name))

        if os.path.isfile(target):
            os.remove(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        else:
            return jsonify({"error": "Modelo no encontrado"}), 404

        return jsonify({"success": True, "deleted": os.path.basename(target)})
    except Exception as e:
        return jsonify({"error": f"Error deleting model: {str(e)}"}), 500

@app.route('/api/get-note', methods=['GET'])
def get_note():
    """Devuelve el contenido de una nota especificada por ID o nombre de archivo"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        note_id = request.args.get('id')
        filename = request.args.get('filename')

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
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
        
        # Verificar SenseVoice (check availability dynamically)
        sensevoice_available = sensevoice_wrapper and sensevoice_wrapper.is_available()
        if sensevoice_available:
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
            "default": "openai" if OPENAI_API_KEY else ("sensevoice" if sensevoice_available else ("local" if WHISPER_CPP_AVAILABLE else None))
        })
        
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('BACKEND_PORT', 8000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    # For large file uploads, we need to ensure proper configuration
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, request_handler=None)
