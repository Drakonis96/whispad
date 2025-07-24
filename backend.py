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
from markdownify import markdownify
from whisper_cpp_wrapper import WhisperCppWrapper
from sensevoice_wrapper import get_sensevoice_wrapper

# Optional import for speaker diarization
try:
    from speaker_diarization import get_speaker_diarization_wrapper
    SPEAKER_DIARIZATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Speaker diarization not available: {e}")
    SPEAKER_DIARIZATION_AVAILABLE = False
    def get_speaker_diarization_wrapper():
        return None

from mermaid import Mermaid
from concept_graph import build_graph, build_concept_graph
import ast
import string
from pydub import AudioSegment

def extract_json(text: str):
    """Try to extract and parse a JSON object from raw text."""
    if not text:
        return None
    # Remove common code block delimiters
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?', '', text)
        text = re.sub(r'```$', '', text)
    # Find the first JSON object in the string
    match = re.search(r'{.*}', text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except Exception:
        pass
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    fixed = fixed.replace("'", '"')
    try:
        return json.loads(fixed)
    except Exception:
        try:
            return ast.literal_eval(text)
        except Exception:
            return None
import threading

# ---------- Path utilities ----------
def sanitize_filename(filename: str) -> str:
    """Return the base name of a filename, removing any path components."""
    return os.path.basename(filename)


def is_path_within_directory(base_dir: str, path: str) -> bool:
    """Check that the absolute path resides within the base directory."""
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(path)
    try:
        return os.path.commonpath([abs_path, abs_base]) == abs_base
    except ValueError:
        return False

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
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
LMSTUDIO_HOST = os.getenv('LMSTUDIO_HOST', '127.0.0.1')
LMSTUDIO_PORT = os.getenv('LMSTUDIO_PORT', '1234')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', '127.0.0.1')
OLLAMA_PORT = os.getenv('OLLAMA_PORT', '11434')
# Enable or disable multi-user support (default True)
MULTI_USER = os.getenv('MULTI_USER', 'true').lower() != 'false'

def load_server_config():
    """Load host/port settings from database if available."""
    global LMSTUDIO_HOST, LMSTUDIO_PORT, OLLAMA_HOST, OLLAMA_PORT
    try:
        from db import get_setting
        LMSTUDIO_HOST = get_setting('lmstudio_host', LMSTUDIO_HOST)
        LMSTUDIO_PORT = get_setting('lmstudio_port', LMSTUDIO_PORT)
        OLLAMA_HOST = get_setting('ollama_host', OLLAMA_HOST)
        OLLAMA_PORT = get_setting('ollama_port', OLLAMA_PORT)
    except Exception:
        # If database is not available or settings don't exist, use defaults
        pass

def save_server_config():
    """Persist current host/port settings to database."""
    try:
        from db import set_setting
        set_setting('lmstudio_host', LMSTUDIO_HOST)
        set_setting('lmstudio_port', LMSTUDIO_PORT)
        set_setting('ollama_host', OLLAMA_HOST)
        set_setting('ollama_port', OLLAMA_PORT)
    except Exception as e:
        print(f"Error saving server config to database: {e}")
        raise

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
ALL_POSTPROCESS_PROVIDERS = ["openai", "google", "openrouter", "lmstudio", "ollama", "groq"]

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from argon2.low_level import Type
from db import (
    init_db,
    migrate_json,
    migrate_server_config_to_db,
    get_user,
    list_users as db_list_users,
    create_user as db_create_user,
    update_password as db_update_password,
    update_user_providers as db_update_user_providers,
    delete_user as db_delete_user,
    get_user_preference,
    set_user_preference,
    get_user_preferences,
)

HASHER = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32, type=Type.ID)

init_db()
migrate_json(hasher=HASHER)
migrate_server_config_to_db()  # Migrate server config from JSON to database

# Load server configuration from database
load_server_config()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD environment variable not set")

def ensure_admin_user():
    admin_user = get_user('admin')
    expected_password_hash = HASHER.hash(ADMIN_PASSWORD)
    
    if not admin_user:
        # Create admin user if it doesn't exist
        db_create_user(
            'admin',
            expected_password_hash,
            True,
            ALL_TRANSCRIPTION_PROVIDERS,
            ALL_POSTPROCESS_PROVIDERS,
        )
    else:
        # Update admin password if it's different from the expected one
        try:
            HASHER.verify(admin_user['password'], ADMIN_PASSWORD)
            # Password is correct, no need to update
        except argon2_exceptions.VerifyMismatchError:
            # Password is different, update it
            print("Updating admin password to match ADMIN_PASSWORD environment variable")
            db_update_password('admin', expected_password_hash)

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
        enable_speaker_diarization = request.form.get('enable_speaker_diarization', 'false').lower() == 'true'

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
            model_filename = sanitize_filename(model_name)
            model_path = os.path.join(models_dir, model_filename)
            if not is_path_within_directory(models_dir, model_path):
                return jsonify({"error": "Invalid model path"}), 400

            result = whisper_wrapper.transcribe_audio_from_bytes(
                audio_bytes,
                audio_file.filename,
                language,
                model_path
            )
            
            if result.get('success'):
                transcription = result.get('transcription', '')
                
                # Apply speaker diarization if enabled
                if enable_speaker_diarization and transcription:
                    try:
                        diarization_wrapper = get_speaker_diarization_wrapper()
                        if diarization_wrapper.is_available() or diarization_wrapper.initialize():
                            segments = diarization_wrapper.diarize_audio_bytes(audio_bytes, audio_file.filename)
                            if segments:
                                transcription = diarization_wrapper.apply_diarization_to_transcription(transcription, segments)
                                print(f"Applied speaker diarization: {len(segments)} segments found")
                        else:
                            print("Speaker diarization not available, continuing without it")
                    except Exception as e:
                        print(f"Error applying speaker diarization: {e}")
                        # Continue without diarization
                
                return jsonify({
                    "transcription": transcription,
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
                transcription = result.get('transcription', '')
                
                # Apply speaker diarization if enabled
                if enable_speaker_diarization and transcription:
                    try:
                        diarization_wrapper = get_speaker_diarization_wrapper()
                        if diarization_wrapper.is_available() or diarization_wrapper.initialize():
                            segments = diarization_wrapper.diarize_audio_bytes(audio_bytes, audio_file.filename)
                            if segments:
                                transcription = diarization_wrapper.apply_diarization_to_transcription(transcription, segments)
                                print(f"Applied speaker diarization: {len(segments)} segments found")
                        else:
                            print("Speaker diarization not available, continuing without it")
                    except Exception as e:
                        print(f"Error applying speaker diarization: {e}")
                        # Continue without diarization
                
                response_data = {
                    "transcription": transcription,
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
                elif provider == 'groq':
                    return chat_groq_stream(messages, model)
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
            elif provider == 'groq':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_groq_stream(text, improvement_type, model, custom_prompt)
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
            elif provider == 'groq':
                model = data.get('model')
                if not model:
                    return jsonify({"error": "Model not specified"}), 400
                return improve_text_groq(text, improvement_type, model, custom_prompt)
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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

def improve_text_groq(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando Groq"""
    if not GROQ_API_KEY:
        return jsonify({"error": "API key de Groq no configurada"}), 500

    if not model:
        return jsonify({"error": "Model not specified"}), 400

    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
        }

        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")

    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
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

    response = requests.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        improved_text = result['choices'][0]['message']['content']
        return jsonify({"improved_text": improved_text})
    else:
        return jsonify({"error": "Error al mejorar el texto"}), response.status_code

def improve_text_groq_stream(text, improvement_type, model, custom_prompt=None):
    """Mejorar texto usando Groq con streaming"""
    if not GROQ_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de Groq no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    if not model:
        def generate_error():
            yield f"data: {json.dumps({'error': 'Model not specified'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = {
            'clarity': f"Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'formal': f"Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'casual': f"Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'academic': f"Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the rewritten text, without additional explanations:\n\n{text}",
            'narrative': f"Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'academic_v2': f"Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'summarize': f"Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the summary, without additional explanations:\n\n{text}",
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
        }

        prompt = prompts.get(improvement_type, f"Improve the following text: {text}")

    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': model,
        'messages': [
            { 'role': 'user', 'content': prompt }
        ],
        'max_tokens': 1000,
        'temperature': 0.7,
        'stream': True
    }

    def generate():
        try:
            response = requests.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'Groq error {response.status_code}'})}\n\n"
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
            yield f"data: {json.dumps({'error': f'Error de conexión con Groq API: {str(e)}'})}\n\n"
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
            'expand': f"Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:\n\n{text}",
            'remove_emoji': f"Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:\n\n{text}",
            'diarization_fix': f"Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:\n\n{text}",
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
                            yield f"data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            # Forward the original OpenAI response format
                            yield f"data: {json.dumps(data)}\n\n"
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
                content = word if word.startswith(' ') else ' ' + word
                yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
            yield f"data: [DONE]\n\n"
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
                            yield f"data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            # Forward the original OpenRouter response format
                            yield f"data: {json.dumps(data)}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

def chat_groq_stream(messages, model):
    if not GROQ_API_KEY:
        def generate_error():
            yield f"data: {json.dumps({'error': 'API key de Groq no configurada'})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})

    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = { 'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json' }
    payload = { 'model': model, 'messages': messages, 'stream': True }

    def generate():
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'Groq error {response.status_code}'})}\n\n"
                return
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() == '[DONE]':
                            yield f"data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            # Forward the original Groq response format
                            yield f"data: {json.dumps(data)}\n\n"
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
                            yield f"data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            # Forward the original LMStudio response format
                            yield f"data: {json.dumps(data)}\n\n"
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
                            content = data['message']['content']
                            yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
                        if data.get('done'):
                            yield f"data: [DONE]\n\n"
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
            new_filename = sanitize_filename(f"{safe_filename}.md")
            new_filepath = os.path.join(saved_notes_dir, new_filename)
            if not is_path_within_directory(saved_notes_dir, new_filepath):
                return jsonify({"error": "Invalid file path"}), 400

            # Buscar archivo existente para esta nota
            existing_filepath = find_existing_note_file(saved_notes_dir, note_id)

            if existing_filepath and existing_filepath != new_filepath:
                # Si el nuevo nombre ya existe y no es el archivo actual, agregar sufijo
                if os.path.exists(new_filepath):
                    counter = 1
                    while True:
                        name_without_ext = os.path.splitext(new_filename)[0]
                        temp_filename = sanitize_filename(f"{name_without_ext}-{counter}.md")
                        temp_filepath = os.path.join(saved_notes_dir, temp_filename)
                        if not is_path_within_directory(saved_notes_dir, temp_filepath):
                            return jsonify({"error": "Invalid file path"}), 400
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
                        temp_filename = sanitize_filename(f"{name_without_ext}-{counter}.md")
                        temp_filepath = os.path.join(saved_notes_dir, temp_filename)
                        if not is_path_within_directory(saved_notes_dir, temp_filepath):
                            return jsonify({"error": "Invalid file path"}), 400
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
                file_content += "*This note is empty*\n"

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

@app.route('/api/create-note-in-folder', methods=['POST'])
def create_note_in_folder():
    """Create a new note directly in a specific folder"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        folder_path = data.get('folder_path', '').strip()
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
            return jsonify({"error": "Note ID is required"}), 400
        
        if not title and not content:
            return jsonify({"error": "Note must have at least a title or content"}), 400
        
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
        with SAVE_LOCK:
            os.makedirs(saved_notes_dir, exist_ok=True)
            
            # Determine target directory
            if folder_path:
                # Handle nested folder paths - sanitize each component separately
                folder_components = folder_path.split('/')
                sanitized_components = [sanitize_filename(component) for component in folder_components if component]
                target_folder_path = os.path.join(*sanitized_components) if sanitized_components else ''
                
                if target_folder_path:
                    target_dir = os.path.join(saved_notes_dir, target_folder_path)
                else:
                    target_dir = saved_notes_dir
            else:
                target_dir = saved_notes_dir
            
            # Security check
            if not is_path_within_directory(saved_notes_dir, target_dir):
                return jsonify({"error": "Invalid folder path"}), 400
            
            # Ensure target directory exists
            os.makedirs(target_dir, exist_ok=True)
            
            # Generate safe filename
            if not title:
                title = "Untitled Note"
            
            safe_filename = generate_safe_filename(title)
            new_filename = sanitize_filename(f"{safe_filename}.md")
            new_filepath = os.path.join(target_dir, new_filename)
            
            if not is_path_within_directory(saved_notes_dir, new_filepath):
                return jsonify({"error": "Invalid file path"}), 400
            
            # Check if file already exists and generate unique name if needed
            if os.path.exists(new_filepath):
                counter = 1
                while True:
                    name_without_ext = os.path.splitext(new_filename)[0]
                    temp_filename = sanitize_filename(f"{name_without_ext}-{counter}.md")
                    temp_filepath = os.path.join(target_dir, temp_filename)
                    if not is_path_within_directory(saved_notes_dir, temp_filepath):
                        return jsonify({"error": "Invalid file path"}), 400
                    if not os.path.exists(temp_filepath):
                        new_filename = temp_filename
                        new_filepath = temp_filepath
                        break
                    counter += 1
            
            # Convert HTML to Markdown if necessary
            markdown_content = html_to_markdown(content) if content else ""
            
            # Create file content
            file_content = f"# {title}\n\n"
            if markdown_content:
                file_content += markdown_content
            else:
                file_content += "*This note is empty*\n"
            
            # Save markdown file
            with open(new_filepath, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Save metadata
            meta_filepath = f"{new_filepath}.meta"
            metadata = {
                "id": note_id,
                "title": title,
                "updated": datetime.now().isoformat(),
                "tags": tags
            }
            with open(meta_filepath, 'w', encoding='utf-8') as meta_file:
                json.dump(metadata, meta_file, ensure_ascii=False, indent=2)
        
        # Send to webhook if configured
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
            "message": "Note created in folder successfully",
            "filename": new_filename,
            "filepath": new_filepath,
            "relative_path": os.path.relpath(new_filepath, saved_notes_dir)
        })
    
    except Exception as e:
        return jsonify({"error": f"Error creating note in folder: {str(e)}"}), 500

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
    """Busca un archivo existente que contenga el ID de nota especificado (búsqueda recursiva)"""
    try:
        # Recursively search all subdirectories for .meta files
        for root, dirs, files in os.walk(saved_notes_dir):
            for filename in files:
                if filename.endswith('.meta'):
                    meta_path = os.path.join(root, filename)
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as meta_file:
                            data = json.load(meta_file)
                        if str(data.get('id')) == str(note_id):
                            # remove both .meta and .md extensions to get base name
                            base = os.path.splitext(os.path.splitext(filename)[0])[0]
                            md_file = os.path.join(root, f"{base}.md")
                            if os.path.exists(md_file):
                                return md_file
                    except Exception:
                        continue
        return None
    except OSError:
        return None

def html_to_markdown(html_content):
    """Convert HTML from the editor into well-formed Markdown."""
    if not html_content:
        return ""

    # Use markdownify for a robust conversion that preserves headings and
    # lists. The custom bullet style ensures compatibility with the
    # markdown parser on the frontend.
    markdown = markdownify(html_content, heading_style="ATX", bullets="-")

    # Normalise whitespace so the resulting markdown is easier to process
    markdown = re.sub(r"\s+\n", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    return markdown.strip()

def sanitize_mermaid_label(text: str) -> str:
    """Remove characters that commonly break Mermaid parsing."""
    if text is None:
        return ''
    text = str(text)
    text = re.sub(r'[\n\r]+', ' ', text)
    text = re.sub(r'[^\w\s.,!\-]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def json_to_mermaid(data, indent=0):
    """Convert a nested dict/list structure to Mermaid mindmap syntax.

    Some providers occasionally return malformed JSON (e.g. subtopics as plain
    strings or objects instead of lists).  This function now tolerates those
    cases by normalising values before recursing instead of raising a
    ``ValueError``.
    """

    lines = []
    if indent == 0:
        lines.append('mindmap')

    # Accept a bare string as a leaf node
    if isinstance(data, str):
        lines.append('  ' * indent + sanitize_mermaid_label(data))
        return lines

    if not isinstance(data, dict):
        raise ValueError('Invalid mindmap data')

    prefix = '  ' * indent
    title = sanitize_mermaid_label(data.get('title') or data.get('topic') or 'Root')
    shape = (data.get('shape') or '').lower()
    icon = data.get('icon')
    class_name = data.get('class') or data.get('className')

    shape_map = {
        'square': ('[', ']'),
        'rounded': ('(', ')'),
        'circle': ('((', '))'),
        'bang': ('))', '(('),
        'cloud': (')', '('),
        'hexagon': ('{{', '}}'),
    }
    if shape in shape_map:
        start, end = shape_map[shape]
        title = f"{start}{title}{end}"

    line = f"{prefix}{title}"
    if icon:
        line += f" ::icon({icon})"
    if class_name:
        line += f" :::{class_name}"
    lines.append(line)

    subtopics = data.get('subtopics', [])
    if isinstance(subtopics, dict):
        subtopics = [subtopics]
    elif isinstance(subtopics, str):
        subtopics = [{'title': subtopics}]

    for child in subtopics:
        lines.extend(json_to_mermaid(child, indent + 1))

    return lines

def timeline_json_to_mermaid(data):
    lines = ["timeline"]
    title = sanitize_mermaid_label(data.get("title"))
    if title:
        lines.append(f"    title {title}")
    for ev in data.get("events", []):
        time = sanitize_mermaid_label(ev.get("time", ""))
        text = sanitize_mermaid_label(ev.get("text", ""))
        lines.append(f"    {time} : {text}")
    return lines

def treemap_json_to_mermaid(data, indent=0):
    """Convert a treemap JSON structure to Mermaid syntax."""
    lines = []
    if indent == 0:
        lines.append("treemap-beta")
    if isinstance(data, str):
        lines.append("  " * indent + f'"{sanitize_mermaid_label(data)}"')
        return lines
    if not isinstance(data, dict):
        raise ValueError("Invalid treemap data")
    prefix = "  " * indent
    title = sanitize_mermaid_label(data.get("title") or data.get("name") or data.get("label") or "Root")
    value = data.get("value")
    class_name = data.get("class") or data.get("className")
    line = f"{prefix}\"{title}\""
    if value is not None:
        line += f": {value}"
    if class_name:
        line += f":::{class_name}"
    lines.append(line)
    children = data.get("children", [])
    if isinstance(children, dict):
        children = [children]
    elif isinstance(children, str):
        children = [{"title": children}]
    for ch in children:
        lines.extend(treemap_json_to_mermaid(ch, indent + 1))
    if indent == 0:
        class_defs = data.get("classDefs") or data.get("classes")
        if isinstance(class_defs, dict):
            for cname, style in class_defs.items():
                lines.append(f"\nclassDef {cname} {style}")
    return lines

def radar_json_to_mermaid(data):
    """Convert radar chart JSON to Mermaid radar-beta syntax."""
    lines = []
    title = sanitize_mermaid_label(data.get("title"))
    if title:
        lines.append("---")
        lines.append(f"title: \"{title}\"")
        lines.append("---")
    lines.append("radar-beta")

    axes = data.get("axis") or data.get("axes") or []
    if isinstance(axes, dict):
        axes = list(axes.values())
    alias_letters = list(string.ascii_lowercase)
    for i in range(0, len(axes), 3):
        group = axes[i:i+3]
        parts = []
        for j, label in enumerate(group):
            alias = alias_letters[i + j]
            parts.append(f"{alias}[\"{sanitize_mermaid_label(label)}\"]")
        lines.append("  axis " + ", ".join(parts))

    for idx, dataset in enumerate(data.get("data", [])):
        alias = alias_letters[idx]
        values = ", ".join(str(v) for v in dataset.get("values", []))
        name = sanitize_mermaid_label(dataset.get("name", f"series{idx+1}"))
        lines.append(f"  curve {alias}[\"{name}\"]{{{values}}}")

    max_val = data.get("max")
    min_val = data.get("min")
    if max_val is not None or min_val is not None:
        lines.append("")
    if max_val is not None:
        lines.append(f"  max {max_val}")
    if min_val is not None:
        lines.append(f"  min {min_val}")
    return lines

def sequence_json_to_mermaid(data):
    lines = ["sequenceDiagram"]
    for msg in data.get("messages", []):
        frm = sanitize_mermaid_label(msg.get("from", ""))
        to = sanitize_mermaid_label(msg.get("to", ""))
        text = sanitize_mermaid_label(msg.get("text", ""))
        lines.append(f"    {frm}->>{to}: {text}")
    return lines

def journey_json_to_mermaid(data):
    lines = ["journey"]
    title = sanitize_mermaid_label(data.get("title"))
    if title:
        lines.append(f"    title {title}")
    for sec in data.get("sections", []):
        lines.append(f"    section {sanitize_mermaid_label(sec.get('name', ''))}")
        for task in sec.get("tasks", []):
            actor = sanitize_mermaid_label(task.get("actor", ""))
            rating = task.get("rating", 0)
            text = sanitize_mermaid_label(task.get("text", ""))
            lines.append(f"        {actor}: {rating}: {text}")
    return lines

def pie_json_to_mermaid(data):
    lines = ["pie"]
    title = sanitize_mermaid_label(data.get("title"))
    if title:
        lines.append(f"    title {title}")
    for item in data.get("items", []):
        label = sanitize_mermaid_label(item.get("label", ""))
        value = item.get("value", 0)
        lines.append(f"    \"{label}\" : {value}")
    return lines

def diagram_json_to_mermaid(diagram_type, data):
    if diagram_type == "mindmap":
        return json_to_mermaid(data)
    if diagram_type == "timeline":
        return timeline_json_to_mermaid(data)
    if diagram_type == "treemap":
        return treemap_json_to_mermaid(data)
    if diagram_type == "radar":
        return radar_json_to_mermaid(data)
    if diagram_type == "sequence":
        return sequence_json_to_mermaid(data)
    if diagram_type == "user journey":
        return journey_json_to_mermaid(data)
    if diagram_type == "pie chart":
        return pie_json_to_mermaid(data)
    raise ValueError("Unsupported diagram type")

def generate_mindmap_openai(note_md, topic, model):
    if not OPENAI_API_KEY:
        return None, 'API key de OpenAI no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = (
        "You create a mind map from a markdown note."
        " Respond only with JSON using this schema:"
        " {\"title\":string, \"subtopics\":[{\"title\":string, \"subtopics\":[]}]}."
    )
    if topic:
        user_msg = f"Expand the topic '{topic}' from this note:\n\n{note_md}"
    else:
        user_msg = note_md
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_msg}
        ]
    }
    resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'OpenAI error'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid JSON returned: {str(e)}'

def generate_mindmap_google(note_md, topic, model):
    if not GOOGLE_API_KEY:
        return None, 'API key de Google no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = (
        "You create a mind map from a markdown note."
        " Respond only with JSON using this schema:"
        " {\"title\":string, \"subtopics\":[{\"title\":string, \"subtopics\":[]}]}"
    )
    user_msg = f"Expand the topic '{topic}' from this note:\n\n{note_md}" if topic else note_md
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_msg}
    ]
    payload = {
        'contents': [
            {
                'role': m['role'],
                'parts': [{'text': m['content']}]
            } for m in messages
        ]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'Google error'
    try:
        result = resp.json()
        content = result['candidates'][0]['content']['parts'][0]['text']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid JSON returned: {str(e)}'

def generate_mindmap_openrouter(note_md, topic, model):
    if not OPENROUTER_API_KEY:
        return None, 'API key de OpenRouter no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = (
        "You create a mind map from a markdown note."
        " Respond only with JSON using this schema:"
        " {\"title\":string, \"subtopics\":[{\"title\":string, \"subtopics\":[]}]}"
    )
    user_msg = f"Expand the topic '{topic}' from this note:\n\n{note_md}" if topic else note_md
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://note-transcribe-ai.local',
        'X-Title': 'Note Transcribe AI'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_msg}
        ]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'OpenRouter error'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid JSON returned: {str(e)}'

def generate_mindmap_groq(note_md, topic, model):
    if not GROQ_API_KEY:
        return None, 'API key de Groq no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = (
        "You create a mind map from a markdown note."
        " Respond only with JSON using this schema:"
        " {\"title\":string, \"subtopics\":[{\"title\":string, \"subtopics\":[]}]}"
    )
    user_msg = f"Expand the topic '{topic}' from this note:\n\n{note_md}" if topic else note_md
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_msg}
        ]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'Groq error'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid JSON returned: {str(e)}'

def generate_mindmap_lmstudio(note_md, topic, model, host, port):
    if not host or not port or not model:
        return None, 'LM Studio host, port and model required'
    system_prompt = (
        "You create a mind map from a markdown note."
        " Respond only with JSON using this schema:"
        " {\"title\":string, \"subtopics\":[{\"title\":string, \"subtopics\":[]}]}"
    )
    user_msg = f"Expand the topic '{topic}' from this note:\n\n{note_md}" if topic else note_md
    url = f"http://{host}:{port}/v1/chat/completions"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_msg}
        ]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
    except requests.RequestException as e:
        return None, str(e)
    if resp.status_code != 200:
        return None, f'LM Studio error {resp.status_code}'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid JSON returned: {str(e)}'

def generate_mindmap_ollama(note_md, topic, model, host, port):
    if not host or not port or not model:
        return None, 'Ollama host, port and model required'
    system_prompt = (
        "You create a mind map from a markdown note."
        " Respond only with JSON using this schema:"
        " {\"title\":string, \"subtopics\":[{\"title\":string, \"subtopics\":[]}]}"
    )
    user_msg = f"Expand the topic '{topic}' from this note:\n\n{note_md}" if topic else note_md
    url = f"http://{host}:{port}/api/chat"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_msg}
        ]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
    except requests.RequestException as e:
        return None, str(e)
    if resp.status_code != 200:
        return None, f'Ollama error {resp.status_code}'
    try:
        result = resp.json()
        if isinstance(result, dict) and 'message' in result and result['message']:
            content = result['message'].get('content', '')
        else:
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid JSON returned: {str(e)}'


def diagram_prompt(diagram_type):
    if diagram_type == 'timeline':
        return ("You create a timeline diagram from a markdown note. "
                "Respond only with JSON using this schema: {\"title\":string, \"events\":[{\"time\":string, \"text\":string}]}.")
    if diagram_type == 'treemap':
        return (
            "You create a treemap from a markdown note. Respond only with JSON "
            "using this schema: {\"title\":string, \"value\"?:number, "
            "\"class\"?:string, \"children\":[{...}], "
            "\"classDefs\"?:{class:string}}."
        )
    if diagram_type == 'radar':
        return (
            "You create a radar chart from a markdown note. Respond only with JSON "
            "using this schema: {\"title\":string, \"axis\":[string], "
            "\"data\":[{\"name\":string, \"values\":[number]}], "
            "\"max\"?:number, \"min\"?:number}."
        )
    if diagram_type == 'sequence':
        return ("You create a sequence diagram from a markdown note. Respond only with JSON using this schema: {\"messages\":[{\"from\":string, \"to\":string, \"text\":string}]}.")
    if diagram_type == 'user journey':
        return ("You create a user journey diagram from a markdown note. Respond only with JSON using this schema: {\"title\":string, \"sections\":[{\"name\":string, \"tasks\":[{\"actor\":string, \"rating\":int, \"text\":string}]}]}.")
    if diagram_type == 'pie chart':
        return ("You create a pie chart from a markdown note. Respond only with JSON using this schema: {\"title\":string, \"items\":[{\"label\":string, \"value\":number}]}.")
    return (
        "You create a mind map from a markdown note. Respond only with JSON "
        "using this schema: {"
        "\"title\":string, \"shape\"?:string, \"icon\"?:string, \"class\"?:string, "
        "\"subtopics\":[{...}]" 
        "}. Allowed shapes: square, rounded, circle, bang, cloud, hexagon."
    )


def generate_diagram_openai(note_md, diagram_type, model):
    if not OPENAI_API_KEY:
        return None, 'API key de OpenAI no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = diagram_prompt(diagram_type)
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': note_md}
        ]
    }
    resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'OpenAI error'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid response: {str(e)}'


def generate_diagram_google(note_md, diagram_type, model):
    if not GOOGLE_API_KEY:
        return None, 'API key de Google no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = diagram_prompt(diagram_type)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': note_md}
    ]
    payload = {
        'contents': [
            {
                'role': m['role'],
                'parts': [{'text': m['content']}]
            } for m in messages
        ]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'Google error'
    try:
        result = resp.json()
        content = result['candidates'][0]['content']['parts'][0]['text']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid response: {str(e)}'


def generate_diagram_openrouter(note_md, diagram_type, model):
    if not OPENROUTER_API_KEY:
        return None, 'API key de OpenRouter no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = diagram_prompt(diagram_type)
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://note-transcribe-ai.local',
        'X-Title': 'Note Transcribe AI'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': note_md}
        ]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'OpenRouter error'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid response: {str(e)}'

def generate_diagram_groq(note_md, diagram_type, model):
    if not GROQ_API_KEY:
        return None, 'API key de Groq no configurada'
    if not model:
        return None, 'Model not specified'
    system_prompt = diagram_prompt(diagram_type)
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': note_md}
        ]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, 'Groq error'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid response: {str(e)}'


def generate_diagram_lmstudio(note_md, diagram_type, model, host, port):
    if not host or not port or not model:
        return None, 'LM Studio host, port and model required'
    system_prompt = diagram_prompt(diagram_type)
    url = f"http://{host}:{port}/v1/chat/completions"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': note_md}
        ]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
    except requests.RequestException as e:
        return None, str(e)
    if resp.status_code != 200:
        return None, f'LM Studio error {resp.status_code}'
    try:
        content = resp.json()['choices'][0]['message']['content']
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid response: {str(e)}'


def generate_diagram_ollama(note_md, diagram_type, model, host, port):
    if not host or not port or not model:
        return None, 'Ollama host, port and model required'
    system_prompt = diagram_prompt(diagram_type)
    url = f"http://{host}:{port}/api/chat"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': note_md}
        ]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
    except requests.RequestException as e:
        return None, str(e)
    if resp.status_code != 200:
        return None, f'Ollama error {resp.status_code}'
    try:
        result = resp.json()
        if isinstance(result, dict) and 'message' in result and result['message']:
            content = result['message'].get('content', '')
        else:
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        data = extract_json(content)
        if data is None:
            return None, 'Invalid JSON returned'
        return data, None
    except Exception as e:
        return None, f'Invalid response: {str(e)}'

@app.route('/api/check-apis', methods=['GET'])
def check_apis():
    """Endpoint para verificar qué APIs están configuradas"""
    apis_status = {
        'openai': bool(OPENAI_API_KEY),
        'google': bool(GOOGLE_API_KEY),
        'deepseek': bool(DEEPSEEK_API_KEY),
        'openrouter': bool(OPENROUTER_API_KEY),
        'groq': bool(GROQ_API_KEY)
    }
    return jsonify(apis_status)


@app.route('/api/mindmap', methods=['POST'])
def generate_mindmap():
    """Generate a mermaid mindmap from note markdown."""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json() or {}
        note = data.get('note', '')
        topic = data.get('topic')
        provider = data.get('provider', 'openai')
        model = data.get('model', 'gpt-3.5-turbo')
        host = data.get('host')
        port = data.get('port')

        if provider == 'openai':
            tree, err = generate_mindmap_openai(note, topic, model)
        elif provider == 'google':
            tree, err = generate_mindmap_google(note, topic, model)
        elif provider == 'openrouter':
            tree, err = generate_mindmap_openrouter(note, topic, model)
        elif provider == 'groq':
            tree, err = generate_mindmap_groq(note, topic, model)
        elif provider == 'lmstudio':
            host = host or LMSTUDIO_HOST
            port = port or LMSTUDIO_PORT
            tree, err = generate_mindmap_lmstudio(note, topic, model, host, port)
        elif provider == 'ollama':
            host = host or OLLAMA_HOST
            port = port or OLLAMA_PORT
            tree, err = generate_mindmap_ollama(note, topic, model, host, port)
        else:
            return jsonify({"error": "Provider not supported"}), 400

        if err:
            return jsonify({"error": err}), 500

        if not isinstance(tree, dict):
            return jsonify({"error": "Invalid JSON returned"}), 500

        mm_lines = json_to_mermaid(tree)
        mm_script = "\n".join(mm_lines)
        svg = Mermaid(mm_script).svg_response.text

        return jsonify({"svg": svg, "tree": tree})
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route('/api/diagram', methods=['POST'])
def generate_diagram():
    """Generate a Mermaid diagram from note markdown."""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json() or {}
        note = data.get('note', '')
        diagram_type = data.get('type', 'mindmap')
        provider = data.get('provider', 'openai')
        model = data.get('model', 'gpt-3.5-turbo')
        host = data.get('host')
        port = data.get('port')

        if diagram_type == 'mindmap':
            topic = data.get('topic')
            if provider == 'openai':
                tree, err = generate_mindmap_openai(note, topic, model)
            elif provider == 'google':
                tree, err = generate_mindmap_google(note, topic, model)
            elif provider == 'openrouter':
                tree, err = generate_mindmap_openrouter(note, topic, model)
            elif provider == 'groq':
                tree, err = generate_mindmap_groq(note, topic, model)
            elif provider == 'lmstudio':
                host = host or LMSTUDIO_HOST
                port = port or LMSTUDIO_PORT
                tree, err = generate_mindmap_lmstudio(note, topic, model, host, port)
            elif provider == 'ollama':
                host = host or OLLAMA_HOST
                port = port or OLLAMA_PORT
                tree, err = generate_mindmap_ollama(note, topic, model, host, port)
            else:
                return jsonify({"error": "Provider not supported"}), 400

            if err:
                return jsonify({"error": err}), 500
            if not isinstance(tree, dict):
                return jsonify({"error": "Invalid JSON returned"}), 500
            mm_lines = json_to_mermaid(tree)
            mm_script = "\n".join(mm_lines)
            svg = Mermaid(mm_script).svg_response.text
            return jsonify({"svg": svg, "tree": tree})

        # other diagram types: convert JSON structure to Mermaid
        if provider == 'openai':
            tree, err = generate_diagram_openai(note, diagram_type, model)
        elif provider == 'google':
            tree, err = generate_diagram_google(note, diagram_type, model)
        elif provider == 'openrouter':
            tree, err = generate_diagram_openrouter(note, diagram_type, model)
        elif provider == 'groq':
            tree, err = generate_diagram_groq(note, diagram_type, model)
        elif provider == 'lmstudio':
            host = host or LMSTUDIO_HOST
            port = port or LMSTUDIO_PORT
            tree, err = generate_diagram_lmstudio(note, diagram_type, model, host, port)
        elif provider == 'ollama':
            host = host or OLLAMA_HOST
            port = port or OLLAMA_PORT
            tree, err = generate_diagram_ollama(note, diagram_type, model, host, port)
        else:
            return jsonify({"error": "Provider not supported"}), 400

        if err:
            return jsonify({"error": err}), 500

        if not isinstance(tree, dict):
            return jsonify({"error": "Invalid JSON returned"}), 500

        lines = diagram_json_to_mermaid(diagram_type, tree)
        script = "\n".join(lines)
        svg = Mermaid(script).svg_response.text
        return jsonify({"svg": svg, "tree": tree})
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route('/api/concept-graph', methods=['POST'])
def concept_graph():
    """Generate a concept co-occurrence graph from note markdown with AI enhancement."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    note = data.get('note', '')
    analysis_type = data.get('analysis_type', 'bridges')  # bridges, hubs, global, local
    language = data.get('language', 'en')  # en, es
    enable_lemmatization = data.get('enable_lemmatization', True)  # lemmatization toggle
    
    # Validate analysis type
    valid_types = ['bridges', 'hubs', 'global', 'local']
    if analysis_type not in valid_types:
        analysis_type = 'bridges'
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Validate lemmatization setting
    if not isinstance(enable_lemmatization, bool):
        enable_lemmatization = True
    
    # Get user's concept exclusions and inclusions
    exclusions = []
    inclusions = []
    try:
        exclusions_str = get_user_preference(username, 'concept_exclusions')
        if exclusions_str:
            exclusions = [word.strip().lower() for word in exclusions_str.split(',') if word.strip()]
    except Exception as e:
        print(f"Error getting concept exclusions: {str(e)}")
        # Continue without exclusions if there's an error
    
    try:
        inclusions_str = get_user_preference(username, 'concept_inclusions')
        if inclusions_str:
            inclusions = [word.strip().lower() for word in inclusions_str.split(',') if word.strip()]
    except Exception as e:
        print(f"Error getting concept inclusions: {str(e)}")
        # Continue without inclusions if there's an error
    
    # Get user's AI provider configuration for enhancement
    user_data = get_user(username)
    ai_provider = None
    api_key = None
    
    if user_data and user_data.get('ai_provider_config'):
        config = user_data['ai_provider_config']
        ai_provider = config.get('provider')
        
        # Get API key based on provider
        if ai_provider == 'openai':
            api_key = config.get('api_key') or OPENAI_API_KEY
        elif ai_provider == 'openrouter':
            api_key = config.get('api_key') or OPENROUTER_API_KEY
        elif ai_provider == 'google':
            api_key = config.get('api_key') or GOOGLE_API_KEY
    
    try:
        # Add timeout for large text processing
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Concept graph generation timed out")
        
        # Set timeout to 30 seconds for very large texts
        text_length = len(note)
        timeout_seconds = 30 if text_length > 50000 else 60
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            # Use enhanced build_graph function with AI support
            if ai_provider and api_key:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Import the async function
                    from concept_graph import build_enhanced_graph_with_ai
                    
                    # No limit on node generation - allow unlimited nodes
                    max_nodes = None  # Remove all node generation limits
                    
                    graph_result = loop.run_until_complete(
                        build_enhanced_graph_with_ai(note, analysis_type, ai_provider, api_key, language=language, enable_lemmatization=enable_lemmatization, exclusions=exclusions, inclusions=inclusions, max_terms=max_nodes)
                    )
                finally:
                    loop.close()
            else:
                # No limit on node generation - allow unlimited nodes
                max_nodes = None  # Remove all node generation limits
                
                graph_result = build_graph(note, analysis_type=analysis_type, language=language, enable_lemmatization=enable_lemmatization, exclusions=exclusions, inclusions=inclusions, max_terms=max_nodes)
        finally:
            signal.alarm(0)  # Cancel the alarm
        
        # Ensure the result has the expected format for frontend
        result = {
            'graph': {
                'nodes': graph_result.get('nodes', []),
                'links': graph_result.get('links', [])
            },
            'insights': graph_result.get('insights', {})
        }
        
        return jsonify(result)
    except TimeoutError:
        return jsonify({"error": "Concept graph generation timed out. Please try with a shorter text or use AI reprocessing to reduce complexity."}), 408
    except Exception as e:
        print(f"Concept graph error: {str(e)}")
        # Fallback to basic graph if enhanced version fails
        try:
            # Try with a more aggressive text truncation for fallback
            truncated_note = note[:20000] if len(note) > 20000 else note
            
            # No limit on node generation for fallback
            fallback_max_nodes = None  # Remove all node generation limits
            
            graph_result = build_graph(truncated_note, analysis_type=analysis_type, language=language, enable_lemmatization=enable_lemmatization, exclusions=exclusions, inclusions=inclusions, max_terms=fallback_max_nodes)
            result = {
                'graph': {
                    'nodes': graph_result.get('nodes', []),
                    'links': graph_result.get('links', [])
                },
                'insights': graph_result.get('insights', {})
            }
            return jsonify(result)
        except Exception as fallback_error:
            return jsonify({"error": f"Error generating graph: {str(fallback_error)}"}), 500


@app.route('/api/concept-graph/ai-reprocess', methods=['POST'])
def concept_graph_ai_reprocess():
    """Reprocess concept graph nodes using AI to select only the most important concepts."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    note = data.get('note', '')
    current_nodes = data.get('current_nodes', [])
    analysis_type = data.get('analysis_type', 'bridges')
    language = data.get('language', 'en')
    enable_lemmatization = data.get('enable_lemmatization', True)
    
    if not note or not current_nodes:
        return jsonify({"error": "Note text and current nodes are required"}), 400
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Validate lemmatization setting
    if not isinstance(enable_lemmatization, bool):
        enable_lemmatization = True
    
    # Get user's configuration from the same file that frontend uses
    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    config_file = os.path.join(user_dir, 'config.json')
    
    ai_provider = None
    api_key = None
    ai_model = None
    host = None
    port = None
    
    # Read configuration from file
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ai_provider = config.get('postprocessProvider')
            ai_model = config.get('postprocessModel')
            
            # Get host/port for local providers
            if ai_provider == 'lmstudio':
                host = config.get('lmstudioHost') or LMSTUDIO_HOST
                port = config.get('lmstudioPort') or LMSTUDIO_PORT
                if not host or not port:
                    return jsonify({"error": "LM Studio host and port not configured"}), 400
            elif ai_provider == 'ollama':
                host = config.get('ollamaHost') or OLLAMA_HOST
                port = config.get('ollamaPort') or OLLAMA_PORT
                if not host or not port:
                    return jsonify({"error": "Ollama host and port not configured"}), 400
            
        except Exception as e:
            return jsonify({"error": f"Error reading user configuration: {str(e)}"}), 500
    
    if not ai_provider:
        return jsonify({"error": "AI provider not configured. Please configure an AI provider in settings."}), 400
    
    # Get API keys from environment variables (they're not stored in user config for security)
    if ai_provider == 'openai':
        api_key = OPENAI_API_KEY
    elif ai_provider == 'openrouter':
        api_key = OPENROUTER_API_KEY
    elif ai_provider == 'google':
        api_key = GOOGLE_API_KEY
    elif ai_provider == 'groq':
        api_key = GROQ_API_KEY
    
    # Check API key for cloud providers
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return jsonify({"error": f"API key not configured for {ai_provider}"}), 400
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Import the async AI reprocessing function
            from ai_reprocess import ai_reprocess_nodes, build_graph_with_selected_nodes
            
            # Convert language parameter from frontend format to backend format
            language_param = 'spanish' if language == 'es' else 'english'
            
            # Prepare arguments based on provider type
            if ai_provider in ['lmstudio', 'ollama']:
                filtered_terms = loop.run_until_complete(
                    ai_reprocess_nodes(note, current_nodes, analysis_type, ai_provider, 
                                     api_key=None, ai_model=ai_model, host=host, port=port, language=language_param, enable_lemmatization=enable_lemmatization)
                )
            else:
                filtered_terms = loop.run_until_complete(
                    ai_reprocess_nodes(note, current_nodes, analysis_type, ai_provider, 
                                     api_key=api_key, language=language_param, enable_lemmatization=enable_lemmatization)
                )
            
            # Regenerate graph with AI-filtered terms (not nodes)
            result = build_graph_with_selected_nodes(note, filtered_terms, analysis_type, language=language_param, enable_lemmatization=enable_lemmatization)
            
            return jsonify(result)
        finally:
            loop.close()
            
    except Exception as e:
        print(f"AI reprocessing error: {str(e)}")
        return jsonify({"error": f"AI reprocessing failed: {str(e)}"}), 500


@app.route('/api/concept-graph/ai-generate-nodes', methods=['POST'])
def concept_graph_ai_generate_nodes():
    """Generate AI-driven super nodes that relate existing concept graph nodes."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    note = data.get('note', '')
    current_nodes = data.get('current_nodes', [])
    language = data.get('language', 'en')
    
    if not note or not current_nodes:
        return jsonify({"error": "Note text and current nodes are required"}), 400
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Get user's configuration from the same file that frontend uses
    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    config_file = os.path.join(user_dir, 'config.json')
    
    ai_provider = None
    api_key = None
    ai_model = None
    host = None
    port = None
    
    # Read configuration from file
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ai_provider = config.get('postprocessProvider')
            ai_model = config.get('postprocessModel')
            
            # Get host/port for local providers
            if ai_provider == 'lmstudio':
                host = config.get('lmstudioHost') or LMSTUDIO_HOST
                port = config.get('lmstudioPort') or LMSTUDIO_PORT
                if not host or not port:
                    return jsonify({"error": "LM Studio host and port not configured"}), 400
            elif ai_provider == 'ollama':
                host = config.get('ollamaHost') or OLLAMA_HOST
                port = config.get('ollamaPort') or OLLAMA_PORT
                if not host or not port:
                    return jsonify({"error": "Ollama host and port not configured"}), 400
            
        except Exception as e:
            return jsonify({"error": f"Error reading user configuration: {str(e)}"}), 500
    
    if not ai_provider:
        return jsonify({"error": "AI provider not configured. Please configure an AI provider in settings."}), 400
    
    # Get API keys from environment variables
    if ai_provider == 'openai':
        api_key = OPENAI_API_KEY
    elif ai_provider == 'openrouter':
        api_key = OPENROUTER_API_KEY
    elif ai_provider == 'google':
        api_key = GOOGLE_API_KEY
    elif ai_provider == 'groq':
        api_key = GROQ_API_KEY
    
    # Check API key for cloud providers
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return jsonify({"error": f"API key not configured for {ai_provider}"}), 400
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Import the async AI node generation function
            from concept_graph import generate_ai_nodes
            
            # Prepare arguments based on provider type
            if ai_provider in ['lmstudio', 'ollama']:
                ai_nodes = loop.run_until_complete(
                    generate_ai_nodes(note, current_nodes, ai_provider, 
                                    api_key=None, ai_model=ai_model, host=host, port=port, language=language)
                )
            else:
                ai_nodes = loop.run_until_complete(
                    generate_ai_nodes(note, current_nodes, ai_provider, 
                                    api_key=api_key, ai_model=ai_model, language=language)
                )
            
            return jsonify({"ai_nodes": ai_nodes})
        finally:
            loop.close()
            
    except Exception as e:
        print(f"AI node generation error: {str(e)}")
        return jsonify({"error": f"AI node generation failed: {str(e)}"}), 500


@app.route('/api/concept-graph/ai-suggestions', methods=['POST'])
def concept_graph_ai_suggestions():
    """Generate AI-based suggestions for bridging concepts, knowledge gaps, and exploration areas."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    note = data.get('note', '')
    current_nodes = data.get('current_nodes', [])
    analysis_type = data.get('analysis_type', 'bridges')
    language = data.get('language', 'en')
    
    if not note or not current_nodes:
        return jsonify({"error": "Note text and current nodes are required"}), 400
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Get user's configuration from the same file that frontend uses (same as chat mode)
    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    config_file = os.path.join(user_dir, 'config.json')
    
    ai_provider = None
    api_key = None
    ai_model = None
    host = None
    port = None
    
    # Read configuration from file (same as ai_reprocess endpoint)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ai_provider = config.get('postprocessProvider')
            ai_model = config.get('postprocessModel')
            
            # Get host/port for local providers
            if ai_provider == 'lmstudio':
                host = config.get('lmstudioHost') or LMSTUDIO_HOST
                port = config.get('lmstudioPort') or LMSTUDIO_PORT
                if not host or not port:
                    return jsonify({"error": "LM Studio host and port not configured"}), 400
            elif ai_provider == 'ollama':
                host = config.get('ollamaHost') or OLLAMA_HOST
                port = config.get('ollamaPort') or OLLAMA_PORT
                if not host or not port:
                    return jsonify({"error": "Ollama host and port not configured"}), 400
            
        except Exception as e:
            return jsonify({"error": f"Error reading user configuration: {str(e)}"}), 500
    
    if not ai_provider:
        return jsonify({"error": "AI provider not configured. Please configure an AI provider in settings."}), 400
    
    # Get API keys from environment variables (they're not stored in user config for security)
    if ai_provider == 'openai':
        api_key = OPENAI_API_KEY
    elif ai_provider == 'openrouter':
        api_key = OPENROUTER_API_KEY
    elif ai_provider == 'google':
        api_key = GOOGLE_API_KEY
    elif ai_provider == 'groq':
        api_key = GROQ_API_KEY
    
    # Check API key for cloud providers
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return jsonify({"error": f"API key not configured for {ai_provider}"}), 400
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Import the AI suggestions function
            from ai_suggestions import generate_ai_suggestions
            
            # Prepare arguments based on provider type
            if ai_provider in ['lmstudio', 'ollama']:
                suggestions = loop.run_until_complete(
                    generate_ai_suggestions(note, current_nodes, analysis_type, ai_provider, 
                                          api_key=None, ai_model=ai_model, host=host, port=port, language=language)
                )
            else:
                suggestions = loop.run_until_complete(
                    generate_ai_suggestions(note, current_nodes, analysis_type, ai_provider, 
                                          api_key=api_key, ai_model=ai_model, language=language)
                )
            
            return jsonify({"suggestions": suggestions})
        finally:
            loop.close()
            
    except Exception as e:
        print(f"AI suggestions error: {str(e)}")
        return jsonify({"error": f"AI suggestions failed: {str(e)}"}), 500


@app.route('/api/concept-graph/ai-single-suggestion', methods=['POST'])
def concept_graph_ai_single_suggestion():
    """Generate a single AI suggestion of the specified type."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    note = data.get('note', '')
    current_nodes = data.get('current_nodes', [])
    suggestion_type = data.get('suggestion_type', 'bridge_concepts')
    analysis_type = data.get('analysis_type', 'bridges')
    language = data.get('language', 'en')
    
    if not note or not current_nodes:
        return jsonify({"error": "Note text and current nodes are required"}), 400
    
    # Validate suggestion type
    valid_types = ['bridge_concepts', 'knowledge_gaps', 'exploration_areas']
    if suggestion_type not in valid_types:
        suggestion_type = 'bridge_concepts'
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Get user's configuration (same as other AI endpoints)
    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    config_file = os.path.join(user_dir, 'config.json')
    
    ai_provider = None
    api_key = None
    ai_model = None
    host = None
    port = None
    
    # Read configuration from file (same as ai_reprocess endpoint)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ai_provider = config.get('postprocessProvider')
            ai_model = config.get('postprocessModel')
            
            # Get host/port for local providers
            if ai_provider == 'lmstudio':
                host = config.get('lmstudioHost') or LMSTUDIO_HOST
                port = config.get('lmstudioPort') or LMSTUDIO_PORT
                if not host or not port:
                    return jsonify({"error": "LM Studio host and port not configured"}), 400
            elif ai_provider == 'ollama':
                host = config.get('ollamaHost') or OLLAMA_HOST
                port = config.get('ollamaPort') or OLLAMA_PORT
                if not host or not port:
                    return jsonify({"error": "Ollama host and port not configured"}), 400
            
        except Exception as e:
            return jsonify({"error": f"Error reading user configuration: {str(e)}"}), 500
    
    if not ai_provider:
        return jsonify({"error": "AI provider not configured. Please configure an AI provider in settings."}), 400
    
    # Get API keys from environment variables (they're not stored in user config for security)
    if ai_provider == 'openai':
        api_key = OPENAI_API_KEY
    elif ai_provider == 'openrouter':
        api_key = OPENROUTER_API_KEY
    elif ai_provider == 'google':
        api_key = GOOGLE_API_KEY
    elif ai_provider == 'groq':
        api_key = GROQ_API_KEY
    
    # Check API key for cloud providers
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return jsonify({"error": f"API key not configured for {ai_provider}"}), 400
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Import the single suggestion function
            from ai_suggestions import generate_single_ai_suggestion
            
            # Prepare arguments based on provider type
            if ai_provider in ['lmstudio', 'ollama']:
                suggestion = loop.run_until_complete(
                    generate_single_ai_suggestion(note, current_nodes, suggestion_type, analysis_type, ai_provider, 
                                                api_key=None, ai_model=ai_model, host=host, port=port, language=language)
                )
            else:
                suggestion = loop.run_until_complete(
                    generate_single_ai_suggestion(note, current_nodes, suggestion_type, analysis_type, ai_provider, 
                                                api_key=api_key, ai_model=ai_model, language=language)
                )
            
            if suggestion:
                return jsonify({"suggestion": suggestion})
            else:
                return jsonify({"error": "Failed to generate suggestion"}), 500
                
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Single AI suggestion error: {str(e)}")
        return jsonify({"error": f"Single suggestion failed: {str(e)}"}), 500


@app.route('/api/concept-graph/ai-custom-suggestion', methods=['POST'])
def concept_graph_ai_custom_suggestion():
    """Generate a custom AI suggestion based on user question."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    question = data.get('question', '')
    note = data.get('note', '')
    current_nodes = data.get('current_nodes', [])
    language = data.get('language', 'en')
    
    if not question or not note:
        return jsonify({"error": "Question and note text are required"}), 400
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Get user's configuration (same as chat mode)
    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    config_file = os.path.join(user_dir, 'config.json')
    
    ai_provider = None
    api_key = None
    ai_model = None
    host = None
    port = None
    
    # Read configuration from file (same as ai_reprocess endpoint)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ai_provider = config.get('postprocessProvider')
            ai_model = config.get('postprocessModel')
            
            # Get host/port for local providers
            if ai_provider == 'lmstudio':
                host = config.get('lmstudioHost') or LMSTUDIO_HOST
                port = config.get('lmstudioPort') or LMSTUDIO_PORT
                if not host or not port:
                    return jsonify({"error": "LM Studio host and port not configured"}), 400
            elif ai_provider == 'ollama':
                host = config.get('ollamaHost') or OLLAMA_HOST
                port = config.get('ollamaPort') or OLLAMA_PORT
                if not host or not port:
                    return jsonify({"error": "Ollama host and port not configured"}), 400
            
        except Exception as e:
            return jsonify({"error": f"Error reading user configuration: {str(e)}"}), 500
    
    if not ai_provider:
        return jsonify({"error": "AI provider not configured. Please configure an AI provider in settings."}), 400
    
    # Get API keys from environment variables (they're not stored in user config for security)
    if ai_provider == 'openai':
        api_key = OPENAI_API_KEY
    elif ai_provider == 'openrouter':
        api_key = OPENROUTER_API_KEY
    elif ai_provider == 'google':
        api_key = GOOGLE_API_KEY
    elif ai_provider == 'groq':
        api_key = GROQ_API_KEY
    
    # Check API key for cloud providers
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return jsonify({"error": f"API key not configured for {ai_provider}"}), 400
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Import the custom suggestion function
            from ai_suggestions import generate_custom_suggestion
            
            # Prepare arguments based on provider type
            if ai_provider in ['lmstudio', 'ollama']:
                suggestion = loop.run_until_complete(
                    generate_custom_suggestion(question, note, current_nodes, ai_provider, 
                                             api_key=None, ai_model=ai_model, host=host, port=port, language=language)
                )
            else:
                suggestion = loop.run_until_complete(
                    generate_custom_suggestion(question, note, current_nodes, ai_provider, 
                                             api_key=api_key, ai_model=ai_model, language=language)
                )
            
            if suggestion:
                return jsonify({
                    "suggestion": suggestion,
                    "type": "custom",
                    "question": question
                })
            else:
                return jsonify({"error": "Failed to generate suggestion"}), 500
                
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Custom AI suggestion error: {str(e)}")
        return jsonify({"error": f"Custom suggestion failed: {str(e)}"}), 500


@app.route('/api/concept-graph/ai-custom-suggestion-stream', methods=['POST'])
def concept_graph_ai_custom_suggestion_stream():
    """Generate a custom AI suggestion with streaming response."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    question = data.get('question', '')
    note = data.get('note', '')
    current_nodes = data.get('current_nodes', [])
    language = data.get('language', 'en')
    
    if not question or not note:
        return jsonify({"error": "Question and note text are required"}), 400
    
    # Validate language
    valid_languages = ['en', 'es']
    if language not in valid_languages:
        language = 'en'
    
    # Get user's configuration (same as chat mode)
    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    config_file = os.path.join(user_dir, 'config.json')
    
    ai_provider = None
    api_key = None
    ai_model = None
    host = None
    port = None
    
    # Read configuration from file (same as chat mode)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ai_provider = config.get('postprocessProvider')
            ai_model = config.get('postprocessModel')
            
            # Get host/port for local providers
            if ai_provider == 'lmstudio':
                host = config.get('lmstudioHost') or LMSTUDIO_HOST
                port = config.get('lmstudioPort') or LMSTUDIO_PORT
            elif ai_provider == 'ollama':
                host = config.get('ollamaHost') or OLLAMA_HOST
                port = config.get('ollamaPort') or OLLAMA_PORT
            
        except Exception as e:
            return jsonify({"error": f"Error reading user configuration: {str(e)}"}), 500
    
    if not ai_provider:
        return jsonify({"error": "AI provider not configured. Please configure an AI provider in settings."}), 400
    
    # Get API keys from environment variables (they're not stored in user config for security)
    if ai_provider == 'openai':
        api_key = OPENAI_API_KEY
    elif ai_provider == 'openrouter':
        api_key = OPENROUTER_API_KEY
    elif ai_provider == 'google':
        api_key = GOOGLE_API_KEY
    elif ai_provider == 'groq':
        api_key = GROQ_API_KEY
    
    # Check API key for cloud providers
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return jsonify({"error": f"API key not configured for {ai_provider}"}), 400
    
    # Extract node labels for context
    node_labels = []
    for node in current_nodes:
        if isinstance(node, dict):
            node_labels.append(node.get('label', ''))
        else:
            node_labels.append(str(node))
    
    # Create custom prompt for streaming
    if language == 'spanish':
        prompt = f"""Basándote en el siguiente texto y conceptos, responde la pregunta del usuario de manera específica y útil.

TEXTO:
{note[:1000]}...

CONCEPTOS ACTUALES:
{', '.join(node_labels)}

PREGUNTA DEL USUARIO:
{question}

INSTRUCCIONES:
- Responde de manera específica y útil
- Relaciona tu respuesta con los conceptos existentes cuando sea relevante
- Proporciona ideas prácticas y accionables
- Mantén un enfoque analítico y constructivo
- Responde en español"""
    else:
        prompt = f"""Based on the following text and concepts, answer the user's question in a specific and helpful way.

TEXT:
{note[:1000]}...

CURRENT CONCEPTS:
{', '.join(node_labels)}

USER QUESTION:
{question}

INSTRUCTIONS:
- Answer specifically and helpfully
- Relate your answer to existing concepts when relevant
- Provide practical and actionable ideas
- Maintain an analytical and constructive focus
- Respond in English"""
    
    # Create messages for streaming (same format as chat mode)
    messages = [{"role": "user", "content": prompt}]
    
    # Use the same streaming functions as chat mode
    try:
        if ai_provider == 'openai':
            return chat_openai_stream(messages, ai_model)
        elif ai_provider == 'google':
            return chat_google_stream(messages, ai_model)
        elif ai_provider == 'openrouter':
            return chat_openrouter_stream(messages, ai_model)
        elif ai_provider == 'groq':
            return chat_groq_stream(messages, ai_model)
        elif ai_provider == 'lmstudio':
            return chat_lmstudio_stream(messages, ai_model, host, port)
        elif ai_provider == 'ollama':
            return chat_ollama_stream(messages, ai_model, host, port)
        else:
            return jsonify({"error": "Provider not supported for streaming"}), 400
    except Exception as e:
        print(f"Streaming AI suggestion error: {str(e)}")
        return jsonify({"error": f"Streaming suggestion failed: {str(e)}"}), 500


@app.route('/api/concept-exclusions', methods=['GET'])
def get_concept_exclusions():
    """Get user's concept exclusion list."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        exclusions_str = get_user_preference(username, 'concept_exclusions')
        if exclusions_str:
            exclusions = [word.strip() for word in exclusions_str.split(',') if word.strip()]
        else:
            exclusions = []
        
        return jsonify({"exclusions": exclusions})
    except Exception as e:
        print(f"Error getting concept exclusions: {str(e)}")
        return jsonify({"error": "Failed to get concept exclusions"}), 500


@app.route('/api/concept-exclusions', methods=['POST'])
def set_concept_exclusions():
    """Set user's concept exclusion list."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    exclusions = data.get('exclusions', [])
    
    # Validate that exclusions is a list
    if not isinstance(exclusions, list):
        return jsonify({"error": "Exclusions must be a list"}), 400
    
    # Clean and validate exclusions
    cleaned_exclusions = []
    for word in exclusions:
        if isinstance(word, str) and word.strip():
            # Basic validation - no special characters except spaces, hyphens, apostrophes
            cleaned_word = word.strip().lower()
            if re.match(r"^[a-zA-Z0-9\s\-'áéíóúüñ]+$", cleaned_word):
                cleaned_exclusions.append(cleaned_word)
    
    try:
        # Save as comma-separated string
        exclusions_str = ','.join(cleaned_exclusions)
        set_user_preference(username, 'concept_exclusions', exclusions_str)
        
        return jsonify({
            "success": True, 
            "exclusions": cleaned_exclusions,
            "message": f"Saved {len(cleaned_exclusions)} concept exclusions"
        })
    except Exception as e:
        print(f"Error setting concept exclusions: {str(e)}")
        return jsonify({"error": "Failed to save concept exclusions"}), 500


@app.route('/api/concept-inclusions', methods=['GET'])
def get_concept_inclusions():
    """Get user's concept inclusion list."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        inclusions_str = get_user_preference(username, 'concept_inclusions')
        if inclusions_str:
            inclusions = [word.strip() for word in inclusions_str.split(',') if word.strip()]
        else:
            inclusions = []
        
        return jsonify({"inclusions": inclusions})
    except Exception as e:
        print(f"Error getting concept inclusions: {str(e)}")
        return jsonify({"error": "Failed to get concept inclusions"}), 500


@app.route('/api/concept-inclusions', methods=['POST'])
def set_concept_inclusions():
    """Set user's concept inclusion list."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    inclusions = data.get('inclusions', [])
    
    # Validate that inclusions is a list
    if not isinstance(inclusions, list):
        return jsonify({"error": "Inclusions must be a list"}), 400
    
    # Clean and validate inclusions
    cleaned_inclusions = []
    for word in inclusions:
        if isinstance(word, str) and word.strip():
            # Basic validation - no special characters except spaces, hyphens, apostrophes
            cleaned_word = word.strip().lower()
            if re.match(r"^[a-zA-Z0-9\s\-'áéíóúüñ]+$", cleaned_word):
                cleaned_inclusions.append(cleaned_word)
    
    try:
        # Save as comma-separated string
        inclusions_str = ','.join(cleaned_inclusions)
        set_user_preference(username, 'concept_inclusions', inclusions_str)
        
        return jsonify({
            "success": True, 
            "inclusions": cleaned_inclusions,
            "message": f"Saved {len(cleaned_inclusions)} concept inclusions"
        })
    except Exception as e:
        print(f"Error setting concept inclusions: {str(e)}")
        return jsonify({"error": "Failed to save concept inclusions"}), 500


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


@app.route('/api/user-styles', methods=['GET', 'POST'])
def user_styles():
    """Load or save custom AI styles for the current user."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    os.makedirs(user_dir, exist_ok=True)
    styles_file = os.path.join(user_dir, 'styles.json')

    if request.method == 'GET':
        if os.path.exists(styles_file):
            try:
                with open(styles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return jsonify({"styles": data})
            except Exception as e:
                return jsonify({"error": f"Error reading styles: {str(e)}"}), 500
        return jsonify({"styles": {}})

    data = request.get_json() or {}
    try:
        with open(styles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Error saving styles: {str(e)}"}), 500


@app.route('/api/user-config', methods=['GET', 'POST'])
def user_config():
    """Load or save config settings for the current user."""
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    user_dir = os.path.join(os.getcwd(), 'user_data', username)
    os.makedirs(user_dir, exist_ok=True)
    config_file = os.path.join(user_dir, 'config.json')

    if request.method == 'GET':
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return jsonify({"config": data})
            except Exception as e:
                return jsonify({"error": f"Error reading config: {str(e)}"}), 500
        return jsonify({"config": {}})

    data = request.get_json() or {}
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Error saving config: {str(e)}"}), 500

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

        # Ensure missing metadata is created for this user's notes (recursively)
        for root, _, files in os.walk(saved_notes_dir):
            for fname in files:
                if not fname.endswith('.md'):
                    continue
                md_path = os.path.join(root, fname)
                meta_path = f"{md_path}.meta"
                if not os.path.exists(meta_path):
                    note_id = parse_note_id_from_md(md_path)
                    if not note_id:
                        note_id = generate_note_id_from_filename(fname)
                    stat = os.stat(md_path)
                    meta_data = {
                        "id": note_id,
                        "title": os.path.splitext(fname)[0],
                        "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "tags": []
                    }
                    try:
                        with open(meta_path, 'w', encoding='utf-8') as mf:
                            json.dump(meta_data, mf, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

        # Recursively list all .md files
        notes = []
        for root, _, files in os.walk(saved_notes_dir):
            for fname in files:
                if not fname.endswith('.md'):
                    continue
                filepath = os.path.join(root, fname)
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
                        "filename": os.path.basename(filepath),
                        "path": os.path.relpath(filepath, saved_notes_dir),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "id": note_id,
                        "tags": tags
                    })
                except Exception as e:
                    print(f"Error al leer información del archivo {fname}: {e}")
        
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
        filename = sanitize_filename(note_file.filename)
        filepath = os.path.join(saved_notes_dir, filename)
        if not is_path_within_directory(saved_notes_dir, filepath):
            return jsonify({"error": "Invalid file path"}), 400
        overwritten = os.path.exists(filepath)
        note_file.save(filepath)

        return jsonify({"success": True, "filename": filename, "overwritten": overwritten})
    except Exception as e:
        return jsonify({"error": f"Error al subir nota: {str(e)}"}), 500

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload and convert PDF/TXT file to markdown text"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Check file extension
        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext not in ['.pdf', '.txt']:
            return jsonify({"error": "Only PDF and TXT files are supported"}), 400

        # Read file content
        file_content = uploaded_file.read()
        
        try:
            if ext == '.txt':
                # For TXT files, simply decode the content
                extracted_text = file_content.decode('utf-8')
            else:
                # For PDF files, use markitdown
                try:
                    from markitdown import MarkItDown
                    md = MarkItDown()
                    
                    # Create a temporary file for markitdown to process
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                        tmp_file.write(file_content)
                        tmp_file_path = tmp_file.name
                    
                    try:
                        result = md.convert(tmp_file_path)
                        extracted_text = result.text_content
                    finally:
                        # Clean up temporary file
                        os.unlink(tmp_file_path)
                        
                except ImportError:
                    return jsonify({"error": "PDF processing not available. markitdown is not installed."}), 500
                except Exception as e:
                    return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500

            # Clean up the extracted text (remove excessive whitespace)
            extracted_text = re.sub(r'\n\s*\n\s*\n', '\n\n', extracted_text.strip())
            
            return jsonify({
                "success": True, 
                "text": extracted_text,
                "filename": uploaded_file.filename
            })
            
        except UnicodeDecodeError:
            return jsonify({"error": "Unable to decode text file. Please ensure it's in UTF-8 format."}), 400
            
    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

def _transcribe_bytes(audio_bytes, filename, language, provider, model=None,
                      detect_emotion=True, detect_events=True, use_itn=True,
                      enable_speaker_diarization=False):
    transcription = ''
    if provider == 'local':
        if not WHISPER_CPP_AVAILABLE:
            raise RuntimeError('Whisper.cpp local no disponible')
        models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
        model_filename = sanitize_filename(model or '')
        model_path = os.path.join(models_dir, model_filename)
        if not is_path_within_directory(models_dir, model_path):
            raise RuntimeError('Invalid model path')
        result = whisper_wrapper.transcribe_audio_from_bytes(audio_bytes, filename, language, model_path)
        if result.get('success'):
            transcription = result.get('transcription', '')
            if enable_speaker_diarization and transcription:
                try:
                    diarization_wrapper = get_speaker_diarization_wrapper()
                    if diarization_wrapper.is_available() or diarization_wrapper.initialize():
                        segments = diarization_wrapper.diarize_audio_bytes(audio_bytes, filename)
                        if segments:
                            transcription = diarization_wrapper.apply_diarization_to_transcription(transcription, segments)
                except Exception:
                    pass
    elif provider == 'sensevoice':
        if not sensevoice_wrapper or not sensevoice_wrapper.is_available():
            raise RuntimeError('SenseVoice no disponible')
        result = sensevoice_wrapper.transcribe_audio_from_bytes(
            audio_bytes,
            filename,
            language,
            detect_emotion,
            detect_events,
            use_itn
        )
        if result.get('success'):
            transcription = result.get('transcription', '')
            if enable_speaker_diarization and transcription:
                try:
                    diarization_wrapper = get_speaker_diarization_wrapper()
                    if diarization_wrapper.is_available() or diarization_wrapper.initialize():
                        segments = diarization_wrapper.diarize_audio_bytes(audio_bytes, filename)
                        if segments:
                            transcription = diarization_wrapper.apply_diarization_to_transcription(transcription, segments)
                except Exception:
                    pass
    else:
        if not OPENAI_API_KEY:
            raise RuntimeError('API key de OpenAI no configurada')
        if not model:
            raise RuntimeError('Model not specified')
        files = {
            'file': (filename, io.BytesIO(audio_bytes), 'application/octet-stream'),
            'model': (None, model)
        }
        if language and language != 'auto':
            files['language'] = (None, language)
        headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
        resp = requests.post('https://api.openai.com/v1/audio/transcriptions', files=files, headers=headers)
        if resp.status_code == 200:
            transcription = resp.json().get('text', '')
        else:
            raise RuntimeError('Error en la transcripción')
    return transcription

def _save_audio_file(audio_bytes, orig_filename, note_id, username):
    with tempfile.NamedTemporaryFile(suffix=f".{orig_filename.split('.')[-1]}", delete=False) as tmp:
        tmp.write(audio_bytes)
        orig_path = tmp.name
    wav_path = whisper_wrapper._convert_to_wav(orig_path, orig_filename)
    os.unlink(orig_path)
    audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
    os.makedirs(audio_dir, exist_ok=True)
    base = sanitize_filename(f"{note_id}-audio")
    counter = 1
    filename = f"{base}{counter}.wav"
    while os.path.exists(os.path.join(audio_dir, filename)):
        counter += 1
        filename = f"{base}{counter}.wav"
    final_path = os.path.join(audio_dir, filename)
    if not is_path_within_directory(audio_dir, final_path):
        raise RuntimeError('Invalid file path')
    shutil.move(wav_path, final_path)
    return filename

@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """Transcribe and store an uploaded audio file linked to a note"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        if 'audio' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400

        note_id = request.form.get('note_id')
        if not note_id:
            return jsonify({"error": "note_id requerido"}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Archivo de audio vacío"}), 400

        language = request.form.get('language') or None
        provider = request.form.get('provider', 'openai')
        model = request.form.get('model')

        skip_save = request.form.get('skip_save', 'false').lower() == 'true'

        detect_emotion = request.form.get('detect_emotion', 'true').lower() == 'true'
        detect_events = request.form.get('detect_events', 'true').lower() == 'true'
        use_itn = request.form.get('use_itn', 'true').lower() == 'true'
        enable_speaker_diarization = request.form.get('enable_speaker_diarization', 'false').lower() == 'true'

        audio_bytes = audio_file.read()

        transcription = _transcribe_bytes(
            audio_bytes,
            audio_file.filename,
            language,
            provider,
            model,
            detect_emotion,
            detect_events,
            use_itn,
            enable_speaker_diarization
        )

        if skip_save:
            return jsonify({"success": True, "transcription": transcription})

        # Convert and save WAV file
        with tempfile.NamedTemporaryFile(suffix=f".{audio_file.filename.split('.')[-1]}", delete=False) as tmp:
            tmp.write(audio_bytes)
            orig_path = tmp.name

        wav_path = whisper_wrapper._convert_to_wav(orig_path, audio_file.filename)
        os.unlink(orig_path)

        audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
        os.makedirs(audio_dir, exist_ok=True)
        base = sanitize_filename(f"{note_id}-audio")
        counter = 1
        filename = f"{base}{counter}.wav"
        while os.path.exists(os.path.join(audio_dir, filename)):
            counter += 1
            filename = f"{base}{counter}.wav"

        final_path = os.path.join(audio_dir, filename)
        if not is_path_within_directory(audio_dir, final_path):
            return jsonify({"error": "Invalid file path"}), 400
        shutil.move(wav_path, final_path)

        return jsonify({"success": True, "transcription": transcription, "filename": filename})
    except Exception as e:
        return jsonify({"error": f"Error al procesar audio: {str(e)}"}), 500

@app.route('/api/upload-audio-stream', methods=['POST'])
def upload_audio_stream():
    """Transcribe an uploaded audio file in chunks and optionally save it"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        if 'audio' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400

        note_id = request.form.get('note_id')
        if not note_id:
            return jsonify({"error": "note_id requerido"}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Archivo de audio vacío"}), 400

        language = request.form.get('language') or None
        provider = request.form.get('provider', 'openai')
        model = request.form.get('model')

        skip_save = request.form.get('skip_save', 'false').lower() == 'true'
        chunk_duration = int(request.form.get('chunk_duration', '30'))

        detect_emotion = request.form.get('detect_emotion', 'true').lower() == 'true'
        detect_events = request.form.get('detect_events', 'true').lower() == 'true'
        use_itn = request.form.get('use_itn', 'true').lower() == 'true'
        enable_speaker_diarization = request.form.get('enable_speaker_diarization', 'false').lower() == 'true'

        audio_bytes = audio_file.read()

        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

        def generate():
            for start_ms in range(0, len(audio), chunk_duration * 1000):
                chunk = audio[start_ms:start_ms + chunk_duration * 1000]
                buf = io.BytesIO()
                chunk.export(buf, format='wav')
                text = _transcribe_bytes(buf.getvalue(), audio_file.filename, language, provider, model,
                                         detect_emotion, detect_events, use_itn, enable_speaker_diarization)
                yield f"data: {json.dumps({'transcription': text})}\n\n"

            filename = None
            if not skip_save:
                filename = _save_audio_file(audio_bytes, audio_file.filename, note_id, username)
                yield f"data: {json.dumps({'done': True, 'filename': filename})}\n\n"
            else:
                yield "data: {\"done\": true}\n\n"

        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        return jsonify({"error": f"Error al procesar audio: {str(e)}"}), 500

@app.route('/api/save-audio', methods=['POST'])
def save_audio():
    """Save a raw audio file linked to a note after converting it to WAV"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        if 'audio' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400

        note_id = request.form.get('note_id')
        if not note_id:
            return jsonify({"error": "note_id requerido"}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Archivo de audio vacío"}), 400

        audio_bytes = audio_file.read()

        with tempfile.NamedTemporaryFile(suffix=f".{audio_file.filename.split('.')[-1]}", delete=False) as tmp:
            tmp.write(audio_bytes)
            orig_path = tmp.name

        wav_path = whisper_wrapper._convert_to_wav(orig_path, audio_file.filename)
        os.unlink(orig_path)

        audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
        os.makedirs(audio_dir, exist_ok=True)
        base = sanitize_filename(f"{note_id}-audio")
        counter = 1
        filename = f"{base}{counter}.wav"
        while os.path.exists(os.path.join(audio_dir, filename)):
            counter += 1
            filename = f"{base}{counter}.wav"

        final_path = os.path.join(audio_dir, filename)
        if not is_path_within_directory(audio_dir, final_path):
            return jsonify({"error": "Invalid file path"}), 400
        shutil.move(wav_path, final_path)

        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"error": f"Error al guardar audio: {str(e)}"}), 500

@app.route('/api/list-audios', methods=['GET'])
def list_audios():
    """Return audio files associated with a note"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        note_id = request.args.get('note_id')
        if not note_id:
            return jsonify({"error": "note_id requerido"}), 400

        audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
        files = []
        if os.path.isdir(audio_dir):
            for fname in os.listdir(audio_dir):
                if fname.startswith(f"{note_id}-audio") and fname.endswith('.wav'):
                    files.append(fname)

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        note_file = find_existing_note_file(saved_notes_dir, note_id)
        title = ''
        if note_file:
            meta = f"{note_file}.meta"
            if os.path.exists(meta):
                try:
                    with open(meta, 'r', encoding='utf-8') as f:
                        title = json.load(f).get('title', '')
                except Exception:
                    pass

        return jsonify({"audios": files, "title": title})
    except Exception as e:
        return jsonify({"error": f"Error al listar audios: {str(e)}"}), 500

@app.route('/api/download-audio', methods=['GET'])
def download_audio():
    """Download an audio file for the current user"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        filename = request.args.get('filename')
        if not filename:
            return jsonify({"error": "filename requerido"}), 400
        audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
        filepath = os.path.join(audio_dir, sanitize_filename(filename))
        if not is_path_within_directory(audio_dir, filepath) or not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": f"Error al descargar audio: {str(e)}"}), 500

@app.route('/api/get-audio', methods=['GET'])
def get_audio():
    """Serve an audio file for playback"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        filename = request.args.get('filename')
        if not filename:
            return jsonify({"error": "filename requerido"}), 400
        audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
        filepath = os.path.join(audio_dir, sanitize_filename(filename))
        if not is_path_within_directory(audio_dir, filepath) or not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
        return send_file(filepath, as_attachment=False, download_name=filename)
    except Exception as e:
        return jsonify({"error": f"Error al obtener audio: {str(e)}"}), 500

@app.route('/api/delete-audio', methods=['POST'])
def delete_audio():
    """Delete an audio file"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json() or {}
        filename = data.get('filename')
        if not filename:
            return jsonify({"error": "filename requerido"}), 400
        audio_dir = os.path.join(os.getcwd(), 'saved_audios', username)
        filepath = os.path.join(audio_dir, sanitize_filename(filename))
        if not is_path_within_directory(audio_dir, filepath) or not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
        os.remove(filepath)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Error al eliminar audio: {str(e)}"}), 500

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
        filename = sanitize_filename(model_file.filename)
        filepath = os.path.join(models_dir, filename)
        if not is_path_within_directory(models_dir, filepath):
            return jsonify({"error": "Invalid file path"}), 400
        overwritten = os.path.exists(filepath)

        # Save incrementally to handle very large files without exhausting memory
        with open(filepath, 'wb') as f:
            for chunk in iter(lambda: model_file.stream.read(8192), b''):
                f.write(chunk)

        return jsonify({"success": True, "filename": filename, "overwritten": overwritten})
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
            filename = os.path.join(models_dir, sanitize_filename(os.path.basename(url)))
            if not is_path_within_directory(models_dir, filename):
                yield f"data: {json.dumps({'error': 'Invalid file path'})}\n\n"
                return

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
        filename = sanitize_filename(name)
        target = os.path.join(models_dir, filename)
        if not is_path_within_directory(models_dir, target):
            return jsonify({"error": "Invalid file path"}), 400

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
            name = sanitize_filename(filename)
            candidate = os.path.join(saved_notes_dir, name)
            if is_path_within_directory(saved_notes_dir, candidate) and os.path.exists(candidate):
                filepath = candidate

        if not filepath:
            return jsonify({"error": "Nota no encontrada"}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        basename = os.path.basename(filepath)

        meta_path = f"{filepath}.meta"
        tags = []
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as meta_file:
                    meta = json.load(meta_file)
                note_id = meta.get('id', note_id)
                tags = meta.get('tags', [])
            except Exception:
                pass

        return jsonify({"filename": basename, "id": note_id, "content": content, "tags": tags})
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

# === FOLDER MANAGEMENT ENDPOINTS ===

@app.route('/api/folders', methods=['GET'])
def list_folders():
    """List all folders for the current user"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
        # Get all folders (directories) in user's notes directory
        folders = []
        if os.path.exists(saved_notes_dir):
            for item in os.listdir(saved_notes_dir):
                item_path = os.path.join(saved_notes_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    folder_info = {
                        "name": item,
                        "path": item,
                        "created": datetime.fromtimestamp(os.path.getctime(item_path)).isoformat(),
                        "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                    }
                    folders.append(folder_info)
        
        # Sort folders by name
        folders.sort(key=lambda x: x['name'].lower())
        
        return jsonify({"folders": folders})
    
    except Exception as e:
        return jsonify({"error": f"Error listing folders: {str(e)}"}), 500

@app.route('/api/folders', methods=['POST'])
def create_folder():
    """Create a new folder"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Folder name is required"}), 400
        
        folder_name = data['name'].strip()
        parent_folder = data.get('parent', '').strip()
        
        if not folder_name:
            return jsonify({"error": "Folder name cannot be empty"}), 400
        
        # Sanitize folder name
        folder_name = sanitize_filename(folder_name)
        if not folder_name:
            return jsonify({"error": "Invalid folder name"}), 400
        
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
        # Build the full folder path
        if parent_folder:
            # Handle nested folder paths - sanitize each component separately
            parent_components = parent_folder.split('/')
            sanitized_parent_components = [sanitize_filename(component) for component in parent_components if component]
            parent_folder_path = os.path.join(*sanitized_parent_components) if sanitized_parent_components else ''
            
            if parent_folder_path:
                folder_path = os.path.join(saved_notes_dir, parent_folder_path, folder_name)
            else:
                folder_path = os.path.join(saved_notes_dir, folder_name)
        else:
            folder_path = os.path.join(saved_notes_dir, folder_name)
        
        # Security check
        if not is_path_within_directory(saved_notes_dir, folder_path):
            return jsonify({"error": "Invalid folder path"}), 400
        
        # If creating a subfolder, ensure parent folder exists (create if necessary)
        if parent_folder and parent_folder_path:
            parent_full_path = os.path.join(saved_notes_dir, parent_folder_path)
            if not os.path.exists(parent_full_path):
                # Create parent directories if they don't exist
                os.makedirs(parent_full_path, exist_ok=True)
        
        # Check if folder already exists
        if os.path.exists(folder_path):
            return jsonify({"error": "Folder already exists"}), 409
        
        # Create the folder
        os.makedirs(folder_path, exist_ok=True)
        
        # Return the relative path from the user's notes directory
        relative_path = os.path.relpath(folder_path, saved_notes_dir)
        
        return jsonify({
            "success": True,
            "folder": {
                "name": folder_name,
                "path": relative_path,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({"error": f"Error creating folder: {str(e)}"}), 500

@app.route('/api/folders/<path:folder_path>', methods=['DELETE'])
def delete_folder(folder_path):
    """Delete a folder. Can delete non-empty folders if force=true is passed."""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        full_folder_path = os.path.join(saved_notes_dir, folder_path)

        # Security check
        if not is_path_within_directory(saved_notes_dir, full_folder_path):
            return jsonify({"error": "Invalid folder path"}), 400

        if not os.path.exists(full_folder_path):
            return jsonify({"error": "Folder not found"}), 404

        if not os.path.isdir(full_folder_path):
            return jsonify({"error": "Path is not a folder"}), 400

        force_delete = request.args.get('force', 'false').lower() == 'true'

        # Check if folder is empty
        if os.listdir(full_folder_path):
            if not force_delete:
                return jsonify({"error": "Folder must be empty before deletion"}), 409
            else:
                shutil.rmtree(full_folder_path)
        else:
            os.rmdir(full_folder_path)

        return jsonify({"success": True, "message": "Folder deleted successfully"})

    except Exception as e:
        return jsonify({"error": f"Error deleting folder: {str(e)}"}), 500

@app.route('/api/move-folder', methods=['POST'])
def move_folder():
    """Move a folder to a different parent folder"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        folder_path = data.get('folder_path', '').strip()
        target_folder = data.get('target_folder', '').strip()

        if not folder_path:
            return jsonify({"error": "Folder path is required"}), 400

        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        source_path = os.path.join(saved_notes_dir, folder_path)

        # Security checks
        if not is_path_within_directory(saved_notes_dir, source_path):
            return jsonify({"error": "Invalid folder path"}), 400

        if not os.path.exists(source_path) or not os.path.isdir(source_path):
            return jsonify({"error": "Folder not found"}), 404

        if target_folder:
            components = target_folder.split('/')
            sanitized = [sanitize_filename(c) for c in components if c]
            target_folder_path = os.path.join(*sanitized) if sanitized else ''
            target_dir = os.path.join(saved_notes_dir, target_folder_path)
        else:
            target_dir = saved_notes_dir

        if not is_path_within_directory(saved_notes_dir, target_dir):
            return jsonify({"error": "Invalid target path"}), 400

        if not os.path.exists(target_dir):
            return jsonify({"error": "Target folder does not exist"}), 404

        # Prevent moving into itself or subfolder
        abs_source = os.path.abspath(source_path)
        abs_target_parent = os.path.abspath(target_dir)
        if abs_target_parent.startswith(abs_source):
            return jsonify({"error": "Cannot move a folder inside itself"}), 400

        folder_name = os.path.basename(source_path)
        target_path = os.path.join(target_dir, folder_name)

        if os.path.exists(target_path):
            return jsonify({"error": "Folder already exists at target location"}), 409

        shutil.move(source_path, target_path)

        relative_new_path = os.path.relpath(target_path, saved_notes_dir)
        return jsonify({
            "success": True,
            "message": "Folder moved successfully",
            "new_path": relative_new_path
        })

    except Exception as e:
        return jsonify({"error": f"Error moving folder: {str(e)}"}), 500

@app.route('/api/move-note', methods=['POST'])
def move_note_to_folder():
    """Move a note to a different folder"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        if not data or 'note_id' not in data:
            return jsonify({"error": "Note ID is required"}), 400
        
        note_id = data['note_id']
        target_folder = data.get('folder', '').strip()  # Empty string means root
        
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
        # Find the current note file
        current_filepath = find_existing_note_file(saved_notes_dir, note_id)
        if not current_filepath:
            return jsonify({"error": "Note not found"}), 404
        
        # Get the filename
        filename = os.path.basename(current_filepath)
        
        # Build target path
        if target_folder:
            # Handle nested folder paths - sanitize each component separately
            folder_components = target_folder.split('/')
            sanitized_components = [sanitize_filename(component) for component in folder_components if component]
            target_folder_path = os.path.join(*sanitized_components) if sanitized_components else ''
            
            if target_folder_path:
                target_dir = os.path.join(saved_notes_dir, target_folder_path)
            else:
                target_dir = saved_notes_dir
            target_filepath = os.path.join(target_dir, filename)
        else:
            target_dir = saved_notes_dir
            target_filepath = os.path.join(target_dir, filename)
        
        # Security check
        if not is_path_within_directory(saved_notes_dir, target_filepath):
            return jsonify({"error": "Invalid target path"}), 400
        
        # Check if target directory exists
        if not os.path.exists(target_dir):
            return jsonify({"error": "Target folder does not exist"}), 404
        
        # Check if file already exists at target location
        if os.path.exists(target_filepath) and target_filepath != current_filepath:
            return jsonify({"error": "A note with this name already exists in the target folder"}), 409
        
        # Move the note file and its metadata
        if target_filepath != current_filepath:
            shutil.move(current_filepath, target_filepath)
            
            # Move metadata file if it exists
            current_meta = f"{current_filepath}.meta"
            target_meta = f"{target_filepath}.meta"
            if os.path.exists(current_meta):
                shutil.move(current_meta, target_meta)
        
        return jsonify({
            "success": True,
            "message": "Note moved successfully",
            "new_path": os.path.relpath(target_filepath, saved_notes_dir)
        })
    
    except Exception as e:
        return jsonify({"error": f"Error moving note: {str(e)}"}), 500

@app.route('/api/folder-structure', methods=['GET'])
def get_folder_structure():
    """Get the complete folder structure with notes"""
    try:
        username = get_current_username()
        if not username:
            return jsonify({"error": "Unauthorized"}), 401
        
        saved_notes_dir = os.path.join(os.getcwd(), 'saved_notes', username)
        
        def build_folder_structure(directory, relative_path=""):
            """Recursively build folder structure"""
            items = []
            
            if not os.path.exists(directory):
                return items
            
            for item in os.listdir(directory):
                if item.startswith('.'):
                    continue
                
                item_path = os.path.join(directory, item)
                item_relative_path = os.path.join(relative_path, item) if relative_path else item
                
                if os.path.isdir(item_path):
                    # It's a folder
                    folder_info = {
                        "type": "folder",
                        "name": item,
                        "path": item_relative_path,
                        "children": build_folder_structure(item_path, item_relative_path)
                    }
                    items.append(folder_info)
                
                elif item.endswith('.md'):
                    # It's a note file
                    try:
                        stat = os.stat(item_path)
                        note_id = None
                        tags = []
                        
                        # Try to get metadata
                        meta_path = f"{item_path}.meta"
                        if os.path.exists(meta_path):
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as meta_file:
                                    meta = json.load(meta_file)
                                note_id = meta.get('id')
                                tags = meta.get('tags', [])
                                if isinstance(tags, list):
                                    tags = [t.lower() for t in tags if isinstance(t, str)]
                            except Exception:
                                pass
                        
                        if not note_id:
                            note_id = generate_note_id_from_filename(item)
                        
                        note_info = {
                            "type": "note",
                            "name": item.replace('.md', ''),
                            "filename": item,
                            "path": item_relative_path,
                            "id": note_id,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "tags": tags
                        }
                        items.append(note_info)
                    
                    except Exception as e:
                        print(f"Error processing note {item}: {e}")
                        continue
            
            # Sort items: folders first, then notes, both alphabetically
            items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
            
            return items
        
        structure = build_folder_structure(saved_notes_dir)
        
        return jsonify({
            "structure": structure,
            "directory": saved_notes_dir
        })
    
    except Exception as e:
        return jsonify({"error": f"Error getting folder structure: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('BACKEND_PORT', 8000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    # For large file uploads, we need to ensure proper configuration
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, request_handler=None)