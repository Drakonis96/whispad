// Configuración del backend - usa rutas relativas ya que nginx hace el proxy
const BACKEND_URL = '';

// Clase para manejar las llamadas al backend
class BackendAPI {
    constructor() {
        this.baseUrl = BACKEND_URL;
    }

    async checkHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch (error) {
            console.error('Error checking backend health:', error);
            return false;
        }
    }

    async checkAPIs() {
        try {
            const response = await fetch(`${this.baseUrl}/api/check-apis`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error('Error checking API status');
        } catch (error) {
            console.error('Error checking APIs:', error);
            return { openai: false, google: false, deepseek: false, openrouter: false, groq: false };
        }
    }

    async transcribeAudio(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'audio.wav');

            const response = await fetch(`${this.baseUrl}/api/transcribe`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            return data.transcription;
        } catch (error) {
            console.error('Error transcribing audio:', error);
            throw error;
        }
    }

    async improveText(text, improvementType, provider = 'openai', stream = true, model = null, host = null, port = null) {
        try {
            if (stream) {
                return this.improveTextStream(text, improvementType, provider, model, host, port);
            } else {
                return this.improveTextNonStream(text, improvementType, provider, model, host, port);
            }
        } catch (error) {
            console.error('Error improving text:', error);
            throw error;
        }
    }

    async improveTextNonStream(text, improvementType, provider = 'openai', model = null, host = null, port = null) {
        try {
            const requestBody = {
                text: text,
                improvement_type: improvementType,
                provider: provider,
                stream: false
            };
            
            if (model) {
                requestBody.model = model;
            }
            if (host) {
                requestBody.host = host;
            }
            if (port) {
                requestBody.port = port;
            }

            const response = await fetch(`${this.baseUrl}/api/improve-text`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            return data.improved_text;
        } catch (error) {
            console.error('Error improving text:', error);
            throw error;
        }
    }

    async improveTextStream(text, improvementType, provider = 'openai', model = null, host = null, port = null) {
        try {
            const requestBody = {
                text: text,
                improvement_type: improvementType,
                provider: provider,
                stream: true
            };
            
            if (model) {
                requestBody.model = model;
            }
            if (host) {
                requestBody.host = host;
            }
            if (port) {
                requestBody.port = port;
            }

            const response = await fetch(`${this.baseUrl}/api/improve-text`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response;
        } catch (error) {
            console.error('Error improving text with streaming:', error);
            throw error;
        }
    }
}

// Instancia global del API backend
const backendAPI = new BackendAPI();
