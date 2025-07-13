// Configuración del backend - usa rutas relativas ya que nginx hace el proxy
const BACKEND_URL = '';

// Clase para manejar las llamadas al backend
class BackendAPI {
    constructor() {
        this.baseUrl = BACKEND_URL;
    }

    async checkHealth() {
        try {
            const response = await authFetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch (error) {
            console.error('Error checking backend health:', error);
            return false;
        }
    }

    async checkAPIs() {
        try {
            const response = await authFetch(`${this.baseUrl}/api/check-apis`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error('Error checking API status');
        } catch (error) {
            console.error('Error checking APIs:', error);
            return { openai: false, google: false, deepseek: false, openrouter: false };
        }
    }

    async transcribeAudio(audioBlob, language = 'auto', model = 'whisper-1', provider = 'openai') {
        try {
            const formData = new FormData();
            
            // Determine file extension based on blob type
            let filename = 'audio.wav';
            if (audioBlob.type) {
                if (audioBlob.type.includes('webm')) {
                    filename = 'audio.webm';
                } else if (audioBlob.type.includes('ogg')) {
                    filename = 'audio.ogg';
                } else if (audioBlob.type.includes('mp4')) {
                    filename = 'audio.mp4';
                }
            }
            
            console.log('Audio blob type:', audioBlob.type, 'Using filename:', filename);
            
            formData.append('audio', audioBlob, filename);
            formData.append('model', model);
            formData.append('provider', provider);
            
            if (language && language !== 'auto') {
                formData.append('language', language);
            }

            console.log('Sending transcription request:', { model, provider, language, filename });

            const response = await authFetch(`${this.baseUrl}/api/transcribe`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Transcription API error:', errorData);
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('Transcription API response:', data);
            
            // Check if we have a valid transcription
            if (!data.transcription && data.transcription !== '') {
                console.error('No transcription field in response:', data);
                throw new Error('Invalid response format: missing transcription field');
            }
            
            if (data.transcription.trim() === '') {
                console.warn('Empty transcription received');
            }
            
            return data.transcription;
        } catch (error) {
            console.error('Error transcribing audio:', error);
            throw error;
        }
    }

    async transcribeAudioSenseVoice(audioBlob, language = 'auto', detectEmotion = true, detectEvents = true, useItn = true) {
        try {
            const formData = new FormData();
            
            // Determine file extension based on blob type
            let filename = 'audio.wav';
            if (audioBlob.type) {
                if (audioBlob.type.includes('webm')) {
                    filename = 'audio.webm';
                } else if (audioBlob.type.includes('ogg')) {
                    filename = 'audio.ogg';
                } else if (audioBlob.type.includes('mp4')) {
                    filename = 'audio.mp4';
                }
            }
            
            console.log('SenseVoice audio blob type:', audioBlob.type, 'Using filename:', filename);
            
            formData.append('audio', audioBlob, filename);
            formData.append('provider', 'sensevoice');
            formData.append('detect_emotion', detectEmotion.toString());
            formData.append('detect_events', detectEvents.toString());
            formData.append('use_itn', useItn.toString());
            
            if (language && language !== 'auto') {
                formData.append('language', language);
            }

            console.log('Sending SenseVoice transcription request:', { 
                language, 
                detectEmotion, 
                detectEvents, 
                useItn, 
                filename 
            });

            const response = await authFetch(`${this.baseUrl}/api/transcribe`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('SenseVoice transcription API error:', errorData);
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('SenseVoice transcription API response:', data);
            
            // Check if we have a valid transcription
            if (!data.transcription && data.transcription !== '') {
                console.error('No transcription field in SenseVoice response:', data);
                throw new Error('Invalid response format: missing transcription field');
            }
            
            if (data.transcription.trim() === '') {
                console.warn('Empty transcription received from SenseVoice');
            }
            
            return data; // Return full data including emotion and events
        } catch (error) {
            console.error('Error transcribing audio with SenseVoice:', error);
            throw error;
        }
    }

    async getTranscriptionProviders() {
        try {
            const response = await authFetch(`${this.baseUrl}/api/transcription-providers`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching transcription providers:', error);
            throw error;
        }
    }

    async improveText(text, improvementType, provider = 'openai', stream = true, model = null, customPrompt = null, host = null, port = null) {
        try {
            if (stream) {
                return this.improveTextStream(text, improvementType, provider, model, customPrompt, host, port);
            } else {
                return this.improveTextNonStream(text, improvementType, provider, model, customPrompt, host, port);
            }
        } catch (error) {
            console.error('Error improving text:', error);
            throw error;
        }
    }

    async improveTextNonStream(text, improvementType, provider = 'openai', model = null, customPrompt = null, host = null, port = null) {
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
            
            if (customPrompt) {
                requestBody.custom_prompt = customPrompt;
            }

            if (host) {
                requestBody.host = host;
            }

            if (port) {
                requestBody.port = port;
            }

            const response = await authFetch(`${this.baseUrl}/api/improve-text`, {
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

    async improveTextStream(text, improvementType, provider = 'openai', model = null, customPrompt = null, host = null, port = null) {
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
            
            if (customPrompt) {
                requestBody.custom_prompt = customPrompt;
            }

            if (host) {
                requestBody.host = host;
            }
            if (port) {
                requestBody.port = port;
            }

            const response = await authFetch(`${this.baseUrl}/api/improve-text`, {
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

    async transcribeAudioGPT4O(audioBlob, options = {}) {
        try {
            console.log('🔧 Backend API: transcribeAudioGPT4O iniciado');
            console.log('AudioBlob:', audioBlob);
            console.log('Options recibidas:', options);
            
            const {
                model = 'gpt-4o-mini-transcribe',
                language = 'auto',
                prompt = null,
                responseFormat = 'json',
                stream = false
            } = options;

            console.log('📝 Opciones procesadas:');
            console.log('- model:', model);
            console.log('- language:', language);
            console.log('- prompt:', prompt);
            console.log('- responseFormat:', responseFormat);
            console.log('- stream:', stream, '(NOTA: OpenAI no soporta streaming para transcripciones)');
            
            // Forzar stream=false porque OpenAI no soporta streaming para transcripciones
            if (stream) {
                console.log('⚠️ Streaming solicitado pero no soportado por OpenAI. Usando modo normal.');
                stream = false;
            }

            // Validar modelo
            if (!['gpt-4o-transcribe', 'gpt-4o-mini-transcribe'].includes(model)) {
                throw new Error("Modelo no válido. Use 'gpt-4o-transcribe' o 'gpt-4o-mini-transcribe'");
            }

            // Validar formato de respuesta
            if (!['json', 'text'].includes(responseFormat)) {
                throw new Error("Formato de respuesta no válido. Use 'json' o 'text'");
            }

            const formData = new FormData();
            formData.append('audio', audioBlob, 'audio.wav');
            formData.append('model', model);
            formData.append('response_format', responseFormat);
            
            console.log('📤 FormData preparado:');
            console.log('- audio:', audioBlob);
            console.log('- model:', model);
            console.log('- response_format:', responseFormat);
            
            if (language && language !== 'auto') {
                formData.append('language', language);
                console.log('- language:', language);
            }
            
            if (prompt) {
                formData.append('prompt', prompt);
                console.log('- prompt:', prompt);
            }
            
            // NO añadir stream porque OpenAI no lo soporta para transcripciones
            
            console.log('� Usando respuesta normal (OpenAI no soporta streaming para transcripciones)');
            // Respuesta normal (no streaming)
            const response = await authFetch(`${this.baseUrl}/api/transcribe-gpt4o`, {
                method: 'POST',
                body: formData
            });

            console.log('📊 Respuesta normal:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Error en respuesta normal:', errorText);
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch {
                    errorData = { error: errorText };
                }
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('✅ Datos recibidos:', data);
            return data.transcription;
        } catch (error) {
            console.error('❌ Error transcribing audio with GPT-4o:', error);
            throw error;
        }
    }

    async processStreamingTranscription(streamResponse, onProgress = null, onComplete = null) {
        try {
            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullTranscription = '';

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Mantener la línea incompleta en el buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data.trim() === '[DONE]') {
                            if (onComplete) {
                                onComplete(fullTranscription);
                            }
                            return fullTranscription;
                        }
                        
                        try {
                            const eventData = JSON.parse(data);
                            if (eventData.error) {
                                throw new Error(eventData.error);
                            }
                            
                            if (eventData.text) {
                                fullTranscription += eventData.text;
                                if (onProgress) {
                                    onProgress(eventData.text, fullTranscription);
                                }
                            } else if (eventData.delta) {
                                fullTranscription += eventData.delta;
                                if (onProgress) {
                                    onProgress(eventData.delta, fullTranscription);
                                }
                            }
                        } catch (parseError) {
                            console.warn('Error parsing streaming data:', parseError);
                        }
                    }
                }
            }

            if (onComplete) {
                onComplete(fullTranscription);
            }
            return fullTranscription;

        } catch (error) {
            console.error('Error processing streaming transcription:', error);
            throw error;
        }
    }

    async getAvailableTranscriptionModels() {
        try {
            return {
                whisper: {
                    model: 'whisper-1',
                    features: ['timestamps', 'verbose_json', 'translations', 'multiple_formats'],
                    streaming: false,
                    description: 'Original Whisper model with full feature support'
                },
                gpt4o_mini: {
                    model: 'gpt-4o-mini-transcribe',
                    features: ['prompting', 'json', 'text'],
                    streaming: true,
                    description: 'Faster GPT-4o model with streaming support'
                },
                gpt4o: {
                    model: 'gpt-4o-transcribe',
                    features: ['prompting', 'json', 'text', 'high_accuracy'],
                    streaming: true,
                    description: 'High-accuracy GPT-4o model with streaming support'
                }
            };
        } catch (error) {
            console.error('Error getting available transcription models:', error);
            throw error;
        }
    }

    async downloadModelStream(size) {
        try {
            const response = await authFetch(`${this.baseUrl}/api/download-model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ size })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response;
        } catch (error) {
            console.error('Error requesting model download:', error);
            throw error;
        }
    }

    async downloadAdvancedModelStream(model) {
        try {
            let endpoint = '';
            switch(model) {
                case 'sensevoice':
                    endpoint = '/api/download-sensevoice';
                    break;
                default:
                    throw new Error(`Unknown model: ${model}`);
            }

            const response = await authFetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response;
        } catch (error) {
            console.error('Error requesting advanced model download:', error);
            throw error;
        }
    }

    async processDownloadStream(streamResponse, onProgress = null) {
        try {
            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        try {
                            const eventData = JSON.parse(data);
                            if (eventData.progress !== undefined && onProgress) {
                                onProgress(eventData.progress);
                            } else if (eventData.error) {
                                throw new Error(eventData.error);
                            } else if (eventData.done) {
                                if (onProgress) onProgress(100);
                                return;
                            }
                        } catch (err) {
                            console.warn('Error parsing download progress:', err);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error processing download stream:', error);
            throw error;
        }
    }

    async processAdvancedDownloadStream(streamResponse, onUpdate = null) {
        try {
            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        try {
                            const eventData = JSON.parse(data);
                            if (onUpdate) {
                                onUpdate(eventData.progress, eventData.status);
                            }
                            if (eventData.error) {
                                throw new Error(eventData.error);
                            } else if (eventData.done) {
                                if (onUpdate) onUpdate(100, 'Download completed');
                                return;
                            }
                        } catch (err) {
                            console.warn('Error parsing advanced download progress:', err);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error processing advanced download stream:', error);
            throw error;
        }
    }

    async listModels() {
        try {
            const response = await authFetch(`${this.baseUrl}/api/list-models`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error listing models:', error);
            throw error;
        }
    }

    async listLmStudioModels(host, port) {
        try {
            const url = `${this.baseUrl}/api/lmstudio/models?host=${encodeURIComponent(host)}&port=${encodeURIComponent(port)}`;
            const response = await authFetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error listing LM Studio models:', error);
            throw error;
        }
    }

    async listOllamaModels(host, port) {
        try {
            const url = `${this.baseUrl}/api/ollama/models?host=${encodeURIComponent(host)}&port=${encodeURIComponent(port)}`;
            const response = await authFetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error listing Ollama models:', error);
            throw error;
        }
    }

    async deleteModel(name) {
        try {
            const response = await authFetch(`${this.baseUrl}/api/delete-model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error deleting model:', error);
            throw error;
        }
    }

    async chatCompletion(messages, provider = 'openai', model = 'gpt-3.5-turbo', host = null, port = null) {
        try {
            const body = { messages, provider, model };
            if (host) body.host = host;
            if (port) body.port = port;
            const response = await authFetch(`${this.baseUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response;
        } catch (error) {
            console.error('Error sending chat message:', error);
            throw error;
        }
    }
    async refreshProviders() {
        try {
            const response = await authFetch(`${this.baseUrl}/api/refresh-providers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error refreshing providers:', error);
            throw error;
        }
    }
}

// Instancia global del API backend
const backendAPI = new BackendAPI();
