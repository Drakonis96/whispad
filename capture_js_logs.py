#!/usr/bin/env python3
"""
Script para capturar logs del test JavaScript ejecutándolo automáticamente
"""

import requests
import json
import time

def simulate_javascript_execution():
    """Simula la ejecución del test JavaScript desde final_test.html"""
    
    print("🔍 Simulando ejecución del test JavaScript de final_test.html")
    print("="*60)
    
    try:
        # Paso 1: Verificar backendAPI (simular)
        print("✅ backendAPI disponible (simulado)")
        
        # Paso 2: Cargar audio como lo hace el JavaScript
        print("📁 Cargando archivo de audio...")
        response = requests.get("http://localhost:5037/test/test.wav")
        if not response.ok:
            raise Exception(f"No se pudo cargar test.wav: {response.status_code}")
        
        audio_data = response.content
        print(f"📄 Audio cargado: {len(audio_data)} bytes")
        
        # Paso 3: Simular transcribeWithOpenAI
        print("🔧 Ejecutando transcribeWithOpenAI...")
        
        mock_config = {
            'transcriptionModel': 'gpt-4o-mini-transcribe',
            'transcriptionLanguage': 'auto',
            'transcriptionPrompt': '',
            'streamingEnabled': False,
            'transcriptionProvider': 'openai'
        }
        
        model = mock_config['transcriptionModel']
        print(f"🎯 Modelo seleccionado: {model}")
        
        # Paso 4: Como incluye 'gpt-4o', simular transcribeWithGPT4O
        if 'gpt-4o' in model:
            print("🔄 Usando GPT-4o transcription...")
            
            # Paso 5: Preparar opciones exactas como el JavaScript
            options = {
                'model': mock_config['transcriptionModel'],
                'language': mock_config['transcriptionLanguage'],
                'responseFormat': 'json',
                'stream': mock_config['streamingEnabled'] and 'gpt-4o' in mock_config['transcriptionModel']
            }
            
            if mock_config['transcriptionPrompt']:
                options['prompt'] = mock_config['transcriptionPrompt']
            
            print(f"⚙️ Opciones: {json.dumps(options, indent=2)}")
            print(f"🌊 Streaming: {options['stream']}")
            
            # Paso 6: Como stream=False, simular transcripción normal
            if not options['stream']:
                print("🔄 Usando transcription normal...")
                print("📞 Llamando backendAPI.transcribeAudioGPT4O...")
                
                # Esta es la llamada REAL que hace el JavaScript
                files = {'audio': ('test.wav', audio_data, 'audio/wav')}
                data = {
                    'model': options['model'],
                    'response_format': options['responseFormat'],
                    'stream': 'false'
                }
                
                if options['language'] and options['language'] != 'auto':
                    data['language'] = options['language']
                
                if options.get('prompt'):
                    data['prompt'] = options['prompt']
                
                print(f"📤 Datos enviados: {data}")
                
                # Hacer la petición EXACTA que hace el JavaScript
                api_response = requests.post(
                    "http://localhost:5037/api/transcribe-gpt4o",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                print(f"📊 Respuesta HTTP: {api_response.status_code}")
                print(f"📋 Headers: {dict(api_response.headers)}")
                
                if api_response.ok:
                    result = api_response.json()
                    transcription = result.get('transcription', '')
                    print(f"✅ Resultado: {transcription}")
                    print("🎉 TEST JAVASCRIPT SIMULADO EXITOSO")
                    return True
                else:
                    error_text = api_response.text
                    print(f"❌ Error HTTP: {error_text}")
                    
                    # Intentar parsear error JSON
                    try:
                        error_json = api_response.json()
                        print(f"❌ Error JSON: {json.dumps(error_json, indent=2)}")
                    except:
                        print("❌ No se pudo parsear error como JSON")
                    
                    print("❌ TEST JAVASCRIPT SIMULADO FALLÓ")
                    return False
            else:
                print("🌊 Streaming habilitado - requiere implementación específica")
                return False
        else:
            print("🔄 Modelo no es GPT-4o")
            return False
            
    except Exception as e:
        print(f"❌ Error en simulación: {e}")
        print("❌ TEST JAVASCRIPT SIMULADO FALLÓ")
        return False

def analyze_potential_frontend_issues():
    """Analiza posibles problemas del frontend"""
    
    print("\n🔍 ANÁLISIS DE POSIBLES PROBLEMAS DEL FRONTEND")
    print("="*60)
    
    # 1. Verificar si backend-api.js se carga correctamente
    print("1. Verificando backend-api.js...")
    try:
        response = requests.get("http://localhost:5037/backend-api.js")
        if response.ok:
            print("✅ backend-api.js accesible")
            
            # Verificar contenido básico
            content = response.text
            if 'class BackendAPI' in content:
                print("✅ Clase BackendAPI encontrada")
            else:
                print("❌ Clase BackendAPI NO encontrada")
                
            if 'transcribeAudioGPT4O' in content:
                print("✅ Método transcribeAudioGPT4O encontrado")
            else:
                print("❌ Método transcribeAudioGPT4O NO encontrado")
                
        else:
            print(f"❌ Error cargando backend-api.js: {response.status_code}")
    except Exception as e:
        print(f"❌ Error verificando backend-api.js: {e}")
    
    # 2. Verificar página principal
    print("\n2. Verificando página principal...")
    try:
        response = requests.get("http://localhost:5037/")
        if response.ok:
            print("✅ Página principal accesible")
            
            content = response.text
            if 'backend-api.js' in content:
                print("✅ backend-api.js referenciado")
            else:
                print("❌ backend-api.js NO referenciado")
                
            if 'app.js' in content:
                print("✅ app.js referenciado")
            else:
                print("❌ app.js NO referenciado")
        else:
            print(f"❌ Error cargando página principal: {response.status_code}")
    except Exception as e:
        print(f"❌ Error verificando página principal: {e}")
    
    # 3. Verificar headers CORS
    print("\n3. Verificando CORS...")
    try:
        response = requests.get("http://localhost:5037/api/check-apis")
        cors_headers = {k: v for k, v in response.headers.items() if 'cors' in k.lower() or 'access-control' in k.lower()}
        if cors_headers:
            print(f"✅ Headers CORS encontrados: {cors_headers}")
        else:
            print("⚠️ No se encontraron headers CORS específicos")
    except Exception as e:
        print(f"❌ Error verificando CORS: {e}")

def main():
    """Función principal"""
    
    # Ejecutar simulación del JavaScript
    success = simulate_javascript_execution()
    
    # Analizar posibles problemas
    analyze_potential_frontend_issues()
    
    print(f"\n📊 RESULTADO FINAL:")
    if success:
        print("✅ La simulación del JavaScript fue EXITOSA")
        print("🎯 El problema puede estar en:")
        print("   - Manejo de promesas/async-await")
        print("   - Event listeners del frontend")
        print("   - Configuración específica del navegador")
        print("   - Interferencia de otros scripts")
    else:
        print("❌ La simulación del JavaScript FALLÓ")
        print("🎯 Se encontraron problemas reales en el backend/API")
    
    print("\n📋 RECOMENDACIÓN:")
    print("1. Abre http://localhost:5037/final_test.html en el navegador")
    print("2. Abre DevTools (F12)")
    print("3. Ve a la pestaña Console")
    print("4. Haz clic en 'Test Exacto del Frontend Principal'")
    print("5. Revisa los mensajes de error en la consola")

if __name__ == "__main__":
    main()
