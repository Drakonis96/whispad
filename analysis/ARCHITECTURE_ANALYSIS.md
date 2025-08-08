# WhisPad 0.7.11 - Architecture Analysis

**Last Updated**: August 8, 2025  
**Version**: 0.7.11.2  
**Analysis Date**: Initial comprehensive analysis

## Table of Contents
1. [System Overview](#system-overview)
2. [Frontend Architecture](#frontend-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Core Components](#core-components)
5. [Data Flow](#data-flow)
6. [API Endpoints](#api-endpoints)
7. [Database Schema](#database-schema)
8. [File Structure](#file-structure)
9. [Configuration Management](#configuration-management)
10. [Change Log](#change-log)

---

## System Overview

WhisPad is a multi-provider voice transcription and AI-enhanced note management platform with the following key characteristics:

- **Architecture**: Client-Server with Flask backend and vanilla JavaScript frontend
- **Database**: PostgreSQL with connection pooling
- **Deployment**: Docker containerization with nginx reverse proxy
- **Authentication**: Session-based with Argon2 password hashing
- **Multi-tenancy**: User isolation with role-based access control

### Technology Stack
```
Frontend: Vanilla JavaScript, HTML5, CSS3, D3.js
Backend: Python Flask, PostgreSQL, Docker
AI Integration: OpenAI, Google AI, OpenRouter, Groq, LM Studio, Ollama
Transcription: OpenAI Whisper API, whisper.cpp, SenseVoice
Audio Processing: Web Audio API, pydub, librosa
```

---

## Frontend Architecture

### Main Application Class (`app.js`)
```javascript
class NotesApp {
    constructor() {
        this.notes = [];              // Note collection
        this.folders = [];            // Folder hierarchy
        this.currentNote = null;      // Active note
        this.config = { /* ... */ };  // User configuration
        this.stylesConfig = { /* */ }; // AI enhancement styles
        this.aiHistory = [];          // Undo/redo for AI changes
        this.chatMessages = [];       // Chat conversation history
    }
}
```

#### Key Responsibilities:
1. **Note Management**: CRUD operations, auto-save, search, tagging
2. **Audio Handling**: Recording, upload, transcription coordination
3. **AI Integration**: Text enhancement, streaming responses, chat interface
4. **UI State Management**: Responsive design, modal handling, mobile optimization
5. **Configuration**: Provider settings, model selection, user preferences

### Backend API Interface (`backend-api.js`)
```javascript
class BackendAPI {
    async transcribeAudio(audioBlob, language, model, provider, enableSpeakerDiarization)
    async improveText(text, improvementType, provider, stream, model, customPrompt)
    async transcribeAudioGPT4O(audioBlob, options)
    async generateMindmap(note, provider, model, topic)
}
```

#### Provider Support Matrix:
| Provider | Transcription | AI Enhancement | Streaming |
|----------|---------------|----------------|-----------|
| OpenAI | ✅ | ✅ | ✅ |
| SenseVoice | ✅ | ❌ | ✅ |
| Local Whisper | ✅ | ❌ | ✅ |
| Google AI | ❌ | ✅ | ✅ (simulated) |
| OpenRouter | ❌ | ✅ | ✅ |
| Groq | ❌ | ✅ | ✅ |
| LM Studio | ❌ | ✅ | ✅ |
| Ollama | ❌ | ✅ | ✅ |

---

## Backend Architecture

### Core Flask Application (`backend.py`)
```python
# Main server with 6,713 lines of code
app = Flask(__name__)

# Key configuration
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4GB for models
CORS(app, origins=cors_origins)

# Global instances
whisper_wrapper = WhisperCppWrapper()
sensevoice_wrapper = get_sensevoice_wrapper()
```

#### Authentication & Session Management
```python
SESSIONS = {}  # Token-based session storage
HASHER = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)

def get_current_username():
    if not MULTI_USER: return 'admin'
    token = request.headers.get('Authorization')
    return SESSIONS.get(token)
```

### Transcription Providers

#### 1. OpenAI Whisper API
- **Endpoint**: `/api/transcribe`
- **Models**: whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe
- **Features**: Auto language detection, custom prompts, streaming (GPT-4o models)

#### 2. Local Whisper.cpp (`whisper_cpp_wrapper.py`)
```python
class WhisperCppWrapper:
    def __init__(self, model_path=None, whisper_cpp_path=None)
    def transcribe_audio(self, audio_file_path, language=None, output_format="json")
    def compile_whisper_cpp(self) -> bool
```
- **Models**: Downloadable .bin files (tiny to large)
- **Compilation**: Dynamic whisper.cpp compilation support
- **Threading**: Multi-threaded processing (`-t 4`)

#### 3. SenseVoice (`sensevoice_wrapper.py`)
```python
class SenseVoiceWrapper:
    def transcribe_audio_from_bytes(self, audio_bytes, filename, language,
                                   detect_emotion=True, detect_events=True, use_itn=True)
```
- **Languages**: 50+ languages with enhanced Asian language support
- **Emotion Detection**: 7 categories (Happy, Sad, Angry, Neutral, etc.)
- **Event Detection**: BGM, Applause, Laughter, Crying, etc.
- **Model Location**: Multiple cache directory support

### AI Text Enhancement Pipeline

#### Provider Implementation Pattern:
```python
def improve_text_[provider](text, improvement_type, model, custom_prompt=None):
    if custom_prompt:
        prompt = f"{custom_prompt}\n\n{text}"
    else:
        prompts = { /* predefined prompts */ }
        prompt = prompts.get(improvement_type, f"Improve: {text}")
    # Provider-specific API call
```

#### Streaming Implementation:
```python
def improve_text_[provider]_stream(text, improvement_type, model, custom_prompt=None):
    def generate():
        # Server-Sent Events implementation
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    return Response(generate(), mimetype='text/event-stream')
```

---

## Core Components

### 1. Audio Processing Pipeline
```mermaid
graph LR
    A[Web Audio API] --> B[MediaRecorder]
    B --> C[Audio Blob]
    C --> D[Format Detection]
    D --> E[Provider Selection]
    E --> F[Transcription Engine]
    F --> G[Speaker Diarization]
    G --> H[Text Enhancement]
    H --> I[Note Integration]
```

### 2. Note Management System
```javascript
// Note data structure
{
    id: "unique-identifier",
    filename: "note.md",
    title: "Note Title", 
    content: "HTML content",
    tags: ["tag1", "tag2"],
    createdAt: "ISO timestamp",
    updatedAt: "ISO timestamp",
    loaded: boolean
}
```

### 3. AI Enhancement Styles
```javascript
const configuracionMejoras = {
    clarity: {
        nombre: "Improve Clarity",
        prompt: "Rewrite the following text in a clearer and more readable way...",
        visible: true
    },
    // ... 12 predefined styles
    // Custom styles supported via UI
}
```

### 4. Concept Graph Engine (`concept_graph.py`)
```python
def build_concept_graph(text, language='en', ai_enhance=False):
    # 3,372 lines of NLP processing
    # - Text preprocessing and tokenization
    # - Multi-language lemmatization (NLTK + spaCy)  
    # - Stopword filtering with comprehensive Spanish support
    # - Concept extraction and relationship mapping
    # - NetworkX graph generation
    # - D3.js visualization data preparation
```

#### Supported Languages:
- **English**: NLTK WordNetLemmatizer
- **Spanish**: Enhanced spaCy + rule-based lemmatization
- **Multi-language**: Basic preprocessing support

### 5. Speaker Diarization (`speaker_diarization.py`)
```python
# Integration with pyannote-audio
def diarize_audio_bytes(audio_bytes, filename):
    # HuggingFace model requirements:
    # - pyannote/speaker-diarization-3.1
    # - pyannote/segmentation-3.0  
    # - speechbrain/spkrec-ecapa-voxceleb
```

### 6. Focus Mode with ESC Key Support
```javascript
// Focus Modal Implementation (app.js lines 10797-10950)
const focusBtn = document.getElementById('focus-btn');
const focusModal = document.getElementById('focus-modal');
const focusEditor = document.getElementById('focus-editor');

// ESC key handler for closing focus modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && focusModal.classList.contains('active')) {
        e.preventDefault();
        closeFocusModal();
    }
});

function closeFocusModal() {
    focusModal.classList.remove('active');
    setTimeout(() => {
        focusModal.style.display = 'none';
        // Sync content back to original editor
        if (originalEditor && focusEditor.innerHTML !== focusOriginalContent) {
            originalEditor.innerHTML = focusEditor.innerHTML;
            originalEditor.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }, 300);
}
```

#### **Focus Mode Features**:
- **Distraction-free writing**: Full-screen editor interface accessible via header "Focus" button
- **Real-time content sync**: Auto-syncs with main editor every 1 second of inactivity
- **AI enhancement**: Dedicated AI buttons for text improvement in focus mode
- **Multiple close methods**: 
  - **ESC key press** (anywhere when focus modal is active) - Primary method
  - Close button (×) in top-right corner
  - Backdrop click (clicking outside the editor area)
- **Content preservation**: Changes in focus mode are automatically synced back to main editor
- **Selection-aware AI**: AI buttons activate only when text is selected within focus editor

#### **ESC Key Behavior Sequence**:
1. **Detection**: Global keydown listener detects ESC key press
2. **Validation**: Checks if focus modal is currently active (`focusModal.classList.contains('active')`)
3. **Prevention**: Prevents default ESC behavior (`e.preventDefault()`)
4. **Animation**: Removes 'active' class to trigger CSS transition
5. **Delay**: 300ms timeout for animation completion
6. **Cleanup**: Hides modal and syncs content changes back to main editor
7. **Event Trigger**: Dispatches 'input' event to update application state

### Extended ESC Key Implementation (Version 0.7.11.2)

```javascript
// Generic ESC key handler for additional modals (Config and Models)
// Note: Focus modal has its own ESC handler and is not affected by this
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && window.notesApp) {
        // Check for Config modal
        const configModal = document.getElementById('config-modal');
        if (configModal && configModal.classList.contains('active')) {
            e.preventDefault();
            window.notesApp.hideConfigModal();
            return;
        }
        
        // Check for Models (upload-model-modal) modal
        const modelsModal = document.getElementById('upload-model-modal');
        if (modelsModal && modelsModal.classList.contains('active')) {
            e.preventDefault();
            window.notesApp.hideUploadModelsModal();
            return;
        }
    }
});
```

**ESC Key Behavior for Additional Modals:**
- **Config Modal**: Closes configuration panel, restores mobile FAB
- **Models Modal**: Closes model management panel, restores mobile FAB  
- **Focus Modal**: Maintains original behavior (unchanged from 0.7.11.1)

**Implementation Benefits:**
- **Non-intrusive**: Focus modal ESC functionality completely preserved
- **Modular**: Easy to extend for future modals
- **Consistent**: Unified keyboard experience across all modals
- **Safe**: Early return prevents multiple modal closures

---

## Data Flow

### Transcription Flow
1. **Audio Capture**: Web Audio API → MediaRecorder
2. **Client Processing**: Format detection, insertion point capture
3. **Server Upload**: FormData with provider/model selection
4. **Provider Routing**: OpenAI API / Local Processing / SenseVoice
5. **Enhancement**: Optional speaker diarization
6. **Response**: JSON with transcription + metadata
7. **Client Integration**: Text insertion at cursor position

### AI Enhancement Flow
1. **Text Selection**: User selects text in editor
2. **Style Selection**: Choose from predefined/custom prompts
3. **Provider Selection**: Based on user permissions
4. **Streaming Request**: Server-Sent Events for real-time updates
5. **History Tracking**: AI changes stored for undo functionality
6. **Auto-save**: Modified notes saved automatically

### Note Management Flow
1. **Creation**: Auto-generated ID + metadata
2. **Storage**: Markdown file + .meta JSON
3. **Database Sync**: PostgreSQL for user preferences
4. **Search/Filter**: Client-side with tag/text filtering
5. **Export**: Individual markdown or ZIP archive

### Keyboard Shortcut Flow
```javascript
// Global keyboard shortcuts (app.js lines 13075-13093)
document.addEventListener('keydown', async (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
            case 's': // Ctrl+S or Cmd+S
                e.preventDefault();
                if (window.notesApp && window.notesApp.currentNote) {
                    window.notesApp.saveCurrentNote();
                }
                break;
            case 'n': // Ctrl+N or Cmd+N  
                e.preventDefault();
                if (window.notesApp) {
                    await window.notesApp.createNewNote();
                }
                break;
        }
    }
    // ESC key handling for Focus mode
    if (e.key === 'Escape' && focusModal.classList.contains('active')) {
        e.preventDefault();
        closeFocusModal();
    }
});
```

#### **Supported Keyboard Shortcuts**:
- **Ctrl+S / Cmd+S**: Save current note
- **Ctrl+N / Cmd+N**: Create new note  
- **ESC**: Exit active modal (Focus, Config, or Models modal)
  - Focus Modal: Content sync and animation
  - Config Modal: Standard modal close
  - Models Modal: Standard modal close

---

## API Endpoints

### Authentication
- `POST /api/login` - User authentication
- `POST /api/logout` - Session termination  
- `GET /api/session-info` - Current session validation

### Transcription
- `POST /api/transcribe` - Multi-provider transcription
- `POST /api/transcribe-gpt4o` - OpenAI GPT-4o specific
- `GET /api/transcription-providers` - Available providers

### AI Enhancement
- `POST /api/improve-text` - Text enhancement (streaming/non-streaming)
- `POST /api/mindmap` - Concept graph generation
- `POST /api/diagram` - Mermaid diagram generation

### Note Management
- `GET /api/list-saved-notes` - Note listing with metadata
- `GET /api/get-note` - Individual note retrieval
- `POST /api/save-note` - Note persistence
- `POST /api/delete-note` - Note deletion
- `POST /api/cleanup-notes` - Metadata migration

### Model Management  
- `GET /api/list-models` - Available whisper.cpp models
- `POST /api/download-model` - Model download with progress
- `POST /api/delete-model` - Model removal
- `POST /api/download-sensevoice` - SenseVoice model download

### User Management (Admin)
- `POST /api/create-user` - User creation
- `GET /api/list-users` - User listing
- `POST /api/update-user-providers` - Provider permissions
- `POST /api/delete-user` - User deletion

### Configuration
- `GET /api/user-config` - User configuration retrieval
- `POST /api/user-config` - Configuration persistence
- `GET /api/user-styles` - AI style configuration  
- `POST /api/user-styles` - Style configuration update

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,                    -- Argon2 hashed
    is_admin BOOLEAN NOT NULL,
    transcription_providers TEXT[] NOT NULL,   -- ["openai", "local", "sensevoice"]
    postprocess_providers TEXT[] NOT NULL      -- ["openai", "google", "openrouter", ...]
);
```

### Settings Table  
```sql
CREATE TABLE settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User Preferences Table
```sql
CREATE TABLE user_preferences (
    username TEXT NOT NULL,
    preference_key VARCHAR(255) NOT NULL,
    preference_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, preference_key),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);
```

### Study Items Table
```sql
CREATE TABLE study_items (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('quiz', 'flashcards')),
    title TEXT NOT NULL,
    content JSONB NOT NULL,
    source_content TEXT,
    note_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## File Structure

```
whispad/
├── analysis/                    # Architecture documentation & change tracking
│   ├── ARCHITECTURE_ANALYSIS.md # Current system architecture documentation
│   ├── CHANGELOG.md             # Detailed version history and change tracking
│   └── UPDATE_GUIDE.md          # Documentation update standards and process
├── api_documentation/           # API reference docs
├── logos/                       # Brand assets
├── logs/                        # nginx logs (Docker volume)
├── saved_notes/                 # Per-user note storage
│   └── {username}/
│       ├── note.md             # Markdown content
│       └── note.md.meta        # JSON metadata
├── saved_audios/               # Audio file storage
├── screenshots/                # Documentation images
├── SenseVoice-main/            # SenseVoice integration
├── test/                       # Test audio files  
├── tests/                      # Test scripts
├── user_data/                  # Legacy user data
├── whisper-cpp-models/         # Local model storage
├── whisper.cpp-main/           # whisper.cpp source
│
├── app.js                      # Main frontend application (13,093 lines)
├── backend-api.js              # API interface (700 lines)
├── backend.py                  # Flask server (6,713 lines)
├── concept_graph.py            # NLP concept extraction (3,372 lines)
├── db.py                       # PostgreSQL interface (485 lines)
├── sensevoice_wrapper.py       # SenseVoice integration (467 lines)
├── speaker_diarization.py      # Speaker identification
├── whisper_cpp_wrapper.py      # Local whisper.cpp (448 lines)
│
├── index.html                  # Main UI
├── login.html                  # Authentication UI
├── style.css                   # Application styles
├── login.js                    # Login functionality
│
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Container definition
├── nginx.conf                  # Reverse proxy config
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
└── env.example                 # Environment template
```

**Total Codebase**: ~25,000+ lines across core components

---

## Configuration Management

### Environment Variables (.env)
```bash
# API Keys
OPENAI_API_KEY=
GOOGLE_API_KEY=
OPENROUTER_API_KEY=
GROQ_API_KEY=
HUGGINGFACE_TOKEN=

# Database
POSTGRES_USER=whispad
POSTGRES_PASSWORD=
POSTGRES_DB=whispad
DATABASE_URL=postgresql://...

# Server Config
ADMIN_PASSWORD=
MULTI_USER=true
CORS_ORIGINS=https://localhost:5037
```

### User Configuration (JavaScript)
```javascript
this.config = {
    transcriptionProvider: '',      // openai|local|sensevoice
    postprocessProvider: '',        // openai|google|openrouter|groq|lmstudio|ollama
    transcriptionModel: '',         // Provider-specific model
    postprocessModel: '',           // AI model selection
    transcriptionLanguage: 'auto',  // Language detection
    streamingEnabled: true,         // Real-time responses
    temperature: 0.3,               // AI creativity
    maxTokens: 1000,               // Response length
    // ... 25+ configuration options
};
```

### Provider Configuration Matrix
| Setting | OpenAI | SenseVoice | Local | Google | OpenRouter | LMStudio | Ollama |
|---------|---------|------------|-------|---------|------------|----------|---------|
| API Key Required | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Local Processing | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Model Download | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Streaming Support | ✅ | ✅ | ✅ | ✅* | ✅ | ✅ | ✅ |
| Custom Prompts | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |

*Simulated streaming for Google AI

---

## Change Log

**Current Version**: 0.7.11.2  
**Last Architecture Update**: August 8, 2025

For detailed change history, version updates, and modification tracking, see [`CHANGELOG.md`](./CHANGELOG.md).

### Architecture Status
- **System Structure**: Current and documented as of version 0.7.11.2
- **Component Analysis**: Complete with all major modules catalogued
- **API Documentation**: Up to date with all endpoints and parameters
- **Database Schema**: Reflects current table structure and relationships
- **Configuration Options**: All settings and environment variables documented

*This analysis document focuses on the current system architecture. All version changes, feature additions, and development history are maintained in the separate changelog file.*

---

## Development Guidelines

### For Future Modifications:
1. **Update this document** when making architectural changes
2. **Maintain version numbers** in change log
3. **Document new components** with similar detail level
4. **Track API changes** in the endpoints section
5. **Update configuration matrix** for new providers
6. **Preserve backward compatibility** when possible

### Code Organization Principles:
- **Single Responsibility**: Each class/module has one clear purpose
- **Provider Pattern**: Consistent interface across different service providers
- **Configuration Driven**: Behavior controlled via config objects
- **Error Handling**: Graceful degradation with user feedback
- **Security First**: User isolation and input validation throughout

This analysis serves as the foundation for understanding WhisPad's architecture and will be maintained as a living document throughout the development lifecycle.
