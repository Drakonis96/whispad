// Datos de ejemplo y configuración
const ejemplosTranscripcion = [
    "Esta es una nota dictada sobre el proyecto de desarrollo web que estamos trabajando en la oficina.",
    "Reunión de equipo programada para mañana a las 10:00 AM para revisar el progreso del trimestre.",
    "Ideas para mejorar la experiencia del usuario en la aplicación móvil que estamos desarrollando.",
    "Lista de tareas pendientes: revisar código, actualizar documentación, preparar presentación para clientes.",
    "Notas de la conferencia sobre inteligencia artificial y sus aplicaciones en el desarrollo web moderno.",
    "Brainstorming de características nuevas para implementar en la próxima versión de la aplicación."
];

const configuracionMejoras = {
    claridad: {
        nombre: "Mejorar Claridad",
        descripcion: "Hace el texto más claro y directo",
        icono: "✨",
        visible: true
    },
    formal: {
        nombre: "Hacer Formal",
        descripcion: "Convierte el texto a un tono más formal",
        icono: "🎩",
        visible: false
    },
    casual: {
        nombre: "Hacer Casual",
        descripcion: "Convierte el texto a un tono más casual",
        icono: "😊",
        visible: false
    },
    academico: {
        nombre: "Académico",
        descripcion: "Convierte el texto a estilo académico",
        icono: "🎓",
        visible: false
    },
    narrativo: {
        nombre: "Narrativo",
        descripcion: "Mejora textos narrativos y diálogos de novela",
        icono: "📖",
        visible: false
    },
    academico_v2: {
        nombre: "Académico v2",
        descripcion: "Mejora académica con cambios mínimos, preservando palabras del autor",
        icono: "🎓",
        visible: true
    },
    resumir: {
        nombre: "Resumir",
        descripcion: "Crea un resumen conciso del texto",
        icono: "📝",
        visible: false
    },
    expandir: {
        nombre: "Expandir",
        descripcion: "Añade más detalles y contexto",
        icono: "✚",
        visible: true
    }
};

// Clase principal de la aplicación
class NotesApp {
    constructor() {
        this.notes = [];
        this.currentNote = null;
        this.isRecording = false;
        this.autoSaveTimeout = null;
        this.searchTerm = '';
        this.selectedText = '';
        this.selectedRange = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        
        // Historia para deshacer cambios de IA
        this.aiHistory = [];
        this.maxHistorySize = 10;
        
        // Configuración de proveedores
        this.config = {
            transcriptionProvider: '',
            postprocessProvider: '',
            transcriptionModel: '',
            postprocessModel: '',
            openaiApiKey: '',
            googleApiKey: '',
            // Configuración avanzada de post-procesamiento
            temperature: 0.3,
            maxTokens: 1000,
            topP: 0.95,
            responseStyle: 'balanced'
        };
        
        this.init();
    }
    
    async init() {
        this.loadConfig();
        this.loadNotes();
        this.setupEventListeners();
        this.renderNotesList();
        this.setupDefaultNote();
        
        // Migrar notas existentes sin ID
        await this.migrateExistingNotes();
    }
    
    async migrateExistingNotes() {
        try {
            const response = await fetch('/api/cleanup-notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.migrated_count > 0) {
                    console.log(`Migradas ${result.migrated_count} notas a la nueva estructura`);
                }
            }
        } catch (error) {
            console.log('Error al migrar notas existentes:', error);
        }
    }
    
    // Configurar event listeners
    setupEventListeners() {
        // Botón nueva nota
        document.getElementById('new-note-btn').addEventListener('click', () => {
            this.createNewNote();
        });
        
        // Búsqueda
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.searchTerm = e.target.value.toLowerCase();
            this.renderNotesList();
        });
        
        // Grabación
        document.getElementById('record-btn').addEventListener('click', () => {
            this.toggleRecording();
        });
        
        // Botones de IA
        document.querySelectorAll('.ai-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.improveText(action);
            });
        });
        
        // Botón deshacer IA
        document.getElementById('undo-ai-btn').addEventListener('click', () => {
            this.undoAIChange();
        });
        
        // Editor
        const editor = document.getElementById('editor');
        editor.addEventListener('input', () => {
            this.handleEditorChange();
        });
        
        // Selección de texto en el editor
        editor.addEventListener('mouseup', () => {
            this.updateSelectedText();
        });
        
        editor.addEventListener('keyup', () => {
            this.updateSelectedText();
        });
        
        // Título de nota
        document.getElementById('note-title').addEventListener('input', () => {
            this.handleTitleChange();
        });
        
        // Botones de formato
        document.querySelectorAll('.format-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const format = e.currentTarget.dataset.format;
                this.applyFormat(format);
            });
        });
        
        // Botones de acción
        document.getElementById('save-btn').addEventListener('click', () => {
            this.saveCurrentNote();
        });
        
        document.getElementById('delete-btn').addEventListener('click', () => {
            this.showDeleteModal();
        });
        
        // Modal de confirmación
        document.getElementById('cancel-delete').addEventListener('click', () => {
            this.hideDeleteModal();
        });
        
        document.getElementById('confirm-delete').addEventListener('click', () => {
            this.deleteCurrentNote();
        });
        
        // Configuración
        document.getElementById('config-btn').addEventListener('click', () => {
            this.showConfigModal();
        });
        
        document.getElementById('cancel-config').addEventListener('click', () => {
            this.hideConfigModal();
        });
        
        document.getElementById('save-config').addEventListener('click', () => {
            this.saveConfig();
        });
        
        // Auto-guardado cada 30 segundos
        setInterval(() => {
            if (this.currentNote) {
                this.saveCurrentNote(true);
            }
        }, 30000);
    }
    
    // Actualizar texto seleccionado
    updateSelectedText() {
        const selection = window.getSelection();
        this.selectedText = selection.toString().trim();
        
        if (this.selectedText && selection.rangeCount > 0) {
            this.selectedRange = selection.getRangeAt(0).cloneRange();
            this.updateAIButtonsState(false);
        } else {
            this.selectedRange = null;
            this.updateAIButtonsState(true);
        }
    }
    
    // Actualizar estado de botones de IA
    updateAIButtonsState(disabled) {
        document.querySelectorAll('.ai-btn').forEach(btn => {
            btn.disabled = disabled;
            btn.style.opacity = disabled ? '0.5' : '1';
        });
    }
    
    // Gestión de notas
    loadNotes() {
        const saved = localStorage.getItem('notes-app-data');
        if (saved) {
            this.notes = JSON.parse(saved);
        } else {
            // Example note on first run
            this.notes = [{
                id: 1,
                title: "Example Note",
                content: "This is a sample note to demonstrate the application's features. You can edit it, delete it or create new notes.",
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            }];
            this.saveToStorage();
        }
    }

    // Configuración
    loadConfig() {
        const saved = localStorage.getItem('notes-app-config');
        if (saved) {
            this.config = { ...this.config, ...JSON.parse(saved) };
        }
    }

    saveConfig() {
        const transcriptionProvider = document.getElementById('transcription-provider').value;
        const postprocessProvider = document.getElementById('postprocess-provider').value;
        const transcriptionModel = document.getElementById('transcription-model').value;
        const postprocessModel = document.getElementById('postprocess-model').value;
        const openaiApiKey = document.getElementById('openai-api-key').value;
        const googleApiKey = document.getElementById('google-api-key').value;
        
        // Configuración avanzada
        const temperature = parseFloat(document.getElementById('temperature-range').value);
        const maxTokens = parseInt(document.getElementById('max-tokens').value);
        const topP = parseFloat(document.getElementById('top-p-range').value);
        const responseStyle = document.getElementById('response-style').value;

        this.config = {
            transcriptionProvider,
            postprocessProvider,
            transcriptionModel,
            postprocessModel,
            openaiApiKey,
            googleApiKey,
            temperature,
            maxTokens,
            topP,
            responseStyle
        };

        localStorage.setItem('notes-app-config', JSON.stringify(this.config));
        this.hideConfigModal();
        this.showNotification('Configuración guardada');
    }

    showConfigModal() {
        document.getElementById('transcription-provider').value = this.config.transcriptionProvider;
        document.getElementById('postprocess-provider').value = this.config.postprocessProvider;
        document.getElementById('transcription-model').value = this.config.transcriptionModel || '';
        document.getElementById('postprocess-model').value = this.config.postprocessModel || '';
        document.getElementById('openai-api-key').value = this.config.openaiApiKey;
        document.getElementById('google-api-key').value = this.config.googleApiKey || '';
        
        // Configuración avanzada
        document.getElementById('temperature-range').value = this.config.temperature || 0.3;
        document.getElementById('max-tokens').value = this.config.maxTokens || 1000;
        document.getElementById('top-p-range').value = this.config.topP || 0.95;
        document.getElementById('response-style').value = this.config.responseStyle || 'balanced';
        
        // Actualizar valores mostrados
        this.updateRangeValues();
        
        const modal = document.getElementById('config-modal');
        modal.classList.add('active');
    }

    hideConfigModal() {
        const modal = document.getElementById('config-modal');
        modal.classList.remove('active');
    }
    
    saveToStorage() {
        localStorage.setItem('notes-app-data', JSON.stringify(this.notes));
    }
    
    createNewNote() {
        const now = new Date();
        const newNote = {
            id: Date.now(),
            title: `Note ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`,
            content: '',
            createdAt: now.toISOString(),
            updatedAt: now.toISOString()
        };
        
        this.notes.unshift(newNote);
        this.saveToStorage();
        this.renderNotesList();
        this.selectNote(newNote.id);
        
        // Enfocar el título para edición
        setTimeout(() => {
            document.getElementById('note-title').focus();
            document.getElementById('note-title').select();
        }, 100);
    }
    
    selectNote(noteId) {
        this.currentNote = this.notes.find(note => note.id === noteId);
        if (this.currentNote) {
            this.loadNoteToEditor();
            this.updateNoteSelection();
        }
    }
    
    loadNoteToEditor() {
        if (!this.currentNote) return;
        
        document.getElementById('note-title').value = this.currentNote.title;
        document.getElementById('editor').innerHTML = this.currentNote.content;
        
        // Habilitar botones
        document.getElementById('save-btn').disabled = false;
        document.getElementById('delete-btn').disabled = false;
        
        // Restablecer selección
        this.selectedText = '';
        this.selectedRange = null;
        this.updateAIButtonsState(true);
        
        // Limpiar historial de IA al cambiar de nota
        this.clearAIHistory();
    }
    
    updateNoteSelection() {
        document.querySelectorAll('.note-item').forEach(item => {
            item.classList.remove('active');
        });
        
        if (this.currentNote) {
            const activeItem = document.querySelector(`[data-note-id="${this.currentNote.id}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
            }
        }
    }
    
    handleEditorChange() {
        if (!this.currentNote) return;
        
        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            this.saveCurrentNote(true);
        }, 2000);
    }
    
    handleTitleChange() {
        if (!this.currentNote) return;
        
        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            this.saveCurrentNote(true);
        }, 1000);
    }
    
    saveCurrentNote(silent = false) {
        if (!this.currentNote) return;
        
        const title = document.getElementById('note-title').value.trim();
        const content = document.getElementById('editor').innerHTML;
        
        this.currentNote.title = title || 'Untitled Note';
        this.currentNote.content = content;
        this.currentNote.updatedAt = new Date().toISOString();
        
        // Save to local storage
        this.saveToStorage();
        this.renderNotesList();
        this.updateNoteSelection();
        
        // Save to server as markdown file
        this.saveNoteToServer(silent);
        
        if (!silent) {
            this.showNotification('Note saved successfully');
        }
    }
    
    async saveNoteToServer(silent = false) {
        if (!this.currentNote) return;
        
        try {
            const response = await fetch('/api/save-note', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: this.currentNote.id,
                    title: this.currentNote.title,
                    content: this.currentNote.content
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!silent && result.success) {
                console.log(`Note saved on server: ${result.filename}`);
            }
        } catch (error) {
            console.error('Error al guardar nota en servidor:', error);
            if (!silent) {
                this.showNotification('Error al guardar nota en servidor', 'error');
            }
        }
    }
    
    deleteCurrentNote() {
        if (!this.currentNote) return;
        
        // Store the note ID before removing it from the array
        const noteIdToDelete = this.currentNote.id;
        
        this.notes = this.notes.filter(note => note.id !== this.currentNote.id);
        this.saveToStorage();
        this.renderNotesList();
        
        // Delete from server
        this.deleteNoteFromServer(noteIdToDelete);
        
        this.currentNote = null;
        this.setupDefaultNote();
        this.hideDeleteModal();
        this.showNotification('Note deleted');
    }
    
    async deleteNoteFromServer(noteId) {
        try {
            const response = await fetch('/api/delete-note', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: noteId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success && result.filename) {
                console.log(`Archivo eliminado del servidor: ${result.filename}`);
            }
        } catch (error) {
            console.error('Error al eliminar nota del servidor:', error);
        }
    }
    
    setupDefaultNote() {
        if (this.notes.length > 0) {
            this.selectNote(this.notes[0].id);
        } else {
            document.getElementById('note-title').value = '';
            document.getElementById('editor').innerHTML = '';
            document.getElementById('save-btn').disabled = true;
            document.getElementById('delete-btn').disabled = true;
        }
    }
    
    // Renderizado de lista
    renderNotesList() {
        const container = document.getElementById('notes-list');
        
        let filteredNotes = this.notes;
        if (this.searchTerm) {
            filteredNotes = this.notes.filter(note => 
                note.title.toLowerCase().includes(this.searchTerm) ||
                note.content.toLowerCase().includes(this.searchTerm)
            );
        }
        
        if (filteredNotes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <h3>No chats yet</h3>
                    <p>Create your first chat to get started</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = filteredNotes.map(note => {
            const preview = this.getTextPreview(note.content);
            const date = new Date(note.createdAt).toLocaleDateString();
            
            return `
                <div class="note-item fade-in" data-note-id="${note.id}">
                    <div class="note-item-title">${note.title}</div>
                    <div class="note-item-preview">${preview}</div>
                    <div class="note-item-date">${date}</div>
                </div>
            `;
        }).join('');
        
        // Agregar event listeners a los items
        container.querySelectorAll('.note-item').forEach(item => {
            item.addEventListener('click', () => {
                const noteId = parseInt(item.dataset.noteId);
                this.selectNote(noteId);
            });
        });
    }
    
    getTextPreview(html) {
        const temp = document.createElement('div');
        temp.innerHTML = html;
        const text = temp.textContent || temp.innerText || '';
        return text.length > 100 ? text.substring(0, 100) + '...' : text;
    }
     // Transcripción
    toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    async startRecording() {
        try {
            // Verificar configuración
            if (this.config.transcriptionProvider === 'openai' && !this.config.openaiApiKey) {
                this.showNotification('Please configure your OpenAI API key', 'warning');
                this.showConfigModal();
                return;
            }

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                await this.transcribeAudio(audioBlob);
                
                // Detener stream
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            
            const recordBtn = document.getElementById('record-btn');
            const recordIcon = document.getElementById('record-icon');
            const recordText = document.getElementById('record-text');
            const recordingStatus = document.getElementById('recording-status');
            const recordingIndicator = document.getElementById('recording-indicator');
            
            recordBtn.classList.add('btn--error');
            recordIcon.className = 'fas fa-stop';
            recordText.textContent = 'Stop';
            recordingStatus.querySelector('.status-text').textContent = 'Recording...';
            recordingIndicator.classList.add('active');

        } catch (error) {
            console.error('Error al acceder al micrófono:', error);
            this.showNotification('Error al acceder al micrófono', 'error');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            const recordBtn = document.getElementById('record-btn');
            const recordIcon = document.getElementById('record-icon');
            const recordText = document.getElementById('record-text');
            const recordingStatus = document.getElementById('recording-status');
            const recordingIndicator = document.getElementById('recording-indicator');
            
            recordBtn.classList.remove('btn--error');
            recordIcon.className = 'fas fa-microphone';
            recordText.textContent = 'Record';
            recordingStatus.querySelector('.status-text').textContent = 'Processing...';
            recordingIndicator.classList.remove('active');
        }
    }

    async transcribeAudio(audioBlob) {
        this.showProcessingOverlay('Transcribing audio...');
        
        try {
            let transcription = '';
            
            if (this.config.transcriptionProvider === 'openai') {
                transcription = await this.transcribeWithOpenAI(audioBlob);
            }
            
            if (transcription) {
                this.insertTranscription(transcription);
                this.showNotification('Transcription complete');
            }
            
        } catch (error) {
            console.error('Transcription error:', error);
            this.showNotification('Error transcribing audio: ' + error.message, 'error');
        } finally {
            this.hideProcessingOverlay();
            document.getElementById('recording-status').querySelector('.status-text').textContent = 'Ready to record';
        }
    }

    async transcribeWithOpenAI(audioBlob) {
        try {
            // Usar el backend en lugar de la API directamente
            return await backendAPI.transcribeAudio(audioBlob);
        } catch (error) {
            throw new Error(`Transcription error: ${error.message}`);
        }
    }

    insertTranscription(transcription) {
        const editor = document.getElementById('editor');
        
        // Enfocar el editor
        editor.focus();
        
        // Obtener posición del cursor o insertar al final
        const selection = window.getSelection();
        let range;
        
        if (selection.rangeCount > 0) {
            range = selection.getRangeAt(0);
        } else {
            range = document.createRange();
            range.selectNodeContents(editor);
            range.collapse(false);
        }
        
        // Insertar texto
        const textNode = document.createTextNode(transcription + ' ');
        range.insertNode(textNode);
        range.setStartAfter(textNode);
        range.setEndAfter(textNode);
        selection.removeAllRanges();
        selection.addRange(range);
        
        // Disparar evento de cambio
        this.handleEditorChange();
    }
    
    // Mejora con IA
    async improveText(action) {
        // Verificar si hay texto seleccionado
        if (!this.selectedText || !this.selectedRange) {
            this.showNotification('Please select text to improve with AI', 'warning');
            return;
        }

        // Verify configuration
        const provider = this.config.postprocessProvider;
        const model = this.config.postprocessModel;
        if (!provider || !model) {
            this.showNotification('Please, select a post-processing provider and model', 'error');
            return;
        }
        const isGemini = provider === 'google';
        const isOpenAI = provider === 'openai';

        if (isOpenAI && !this.config.openaiApiKey) {
            this.showNotification('Please configure your OpenAI API key', 'warning');
            this.showConfigModal();
            return;
        }

        if (isGemini && !this.config.googleApiKey) {
            this.showNotification('Please configure your Google AI API key', 'warning');
            this.showConfigModal();
            return;
        }

        // Guardar estado actual para poder deshacer
        this.saveAIHistory();

        this.showProcessingOverlay(`Improving text with AI...`);
        
        try {
            let improvedText = '';
            
            if (isOpenAI) {
                improvedText = await this.improveWithOpenAI(this.selectedText, action);
            } else if (isGemini) {
                improvedText = await this.improveWithGemini(this.selectedText, action);
            } else {
                // Fallback a mejora local
                improvedText = this.applyAIImprovement(this.selectedText, action);
            }
            
            // Restaurar selección y reemplazar texto
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(this.selectedRange);
            
            // Reemplazar texto seleccionado
            this.selectedRange.deleteContents();
            this.selectedRange.insertNode(document.createTextNode(improvedText));
            
            // Limpiar selección
            selection.removeAllRanges();
            this.selectedText = '';
            this.selectedRange = null;
            this.updateAIButtonsState(true);
            
            // Habilitar botón de deshacer
            this.updateUndoButton();
            
            this.hideProcessingOverlay();
            this.showNotification(`Text improved: ${configuracionMejoras[action].nombre}`);
            this.handleEditorChange();
            
        } catch (error) {
            this.hideProcessingOverlay();
            console.error('Error improving text:', error);
            this.showNotification('Error improving text: ' + error.message, 'error');
        }
    }

    async improveWithOpenAI(text, action) {
        const prompts = {
            claridad: `Mejora la claridad del siguiente texto, hazlo más directo y fácil de entender. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            formal: `Convierte el siguiente texto a un tono más formal y profesional. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            casual: `Convierte el siguiente texto a un tono más casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            academico: `Convierte el siguiente texto a estilo académico con vocabulario técnico, estructura formal y referencias implícitas. Utiliza un lenguaje preciso, objetivo y bien fundamentado. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            narrativo: `Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto:\n\n${text}`,
            academico_v2: `Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible:\n\n${text}`,
            resumir: `Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            expandir: `Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`
        };

        const model = this.config.postprocessModel || 'gpt-4o-mini';
        
        // Aplicar configuración según el estilo de respuesta
        let temperature = this.config.temperature || 0.3;
        let topP = this.config.topP || 0.95;
        
        if (this.config.responseStyle === 'factual') {
            temperature = 0.2;
            topP = 0.9;
        } else if (this.config.responseStyle === 'creative') {
            temperature = 0.7;
            topP = 0.95;
        }

        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.config.openaiApiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: model,
                messages: [
                    {
                        role: 'system',
                        content: 'Eres un asistente que ayuda a mejorar textos. Responde únicamente con el texto mejorado, sin explicaciones adicionales.'
                    },
                    {
                        role: 'user',
                        content: prompts[action] || prompts.claridad
                    }
                ],
                max_tokens: this.config.maxTokens || 1000,
                temperature: temperature,
                top_p: topP
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error?.message || `HTTP ${response.status}`);
        }

        const data = await response.json();
        return data.choices[0]?.message?.content || text;
    }

    async improveWithGemini(text, action) {
        const prompts = {
            claridad: `Mejora la claridad del siguiente texto, hazlo más directo y fácil de entender. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            formal: `Convierte el siguiente texto a un tono más formal y profesional. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            casual: `Convierte el siguiente texto a un tono más casual y amigable. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            academico: `Convierte el siguiente texto a estilo académico con vocabulario técnico, estructura formal y referencias implícitas. Utiliza un lenguaje preciso, objetivo y bien fundamentado. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            narrativo: `Mejora el siguiente texto narrativo o diálogo de novela, preservando el estilo literario y la voz narrativa. Mejora la fluidez, la descripción y la calidad literaria manteniendo la esencia del texto:\n\n${text}`,
            academico_v2: `Mejora el siguiente texto académico realizando cambios mínimos para preservar las palabras del autor. Usa palabras más precisas cuando sea necesario, mejora la estructura y elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta. Mantén el estilo y vocabulario original tanto como sea posible:\n\n${text}`,
            resumir: `Crea un resumen conciso del siguiente texto. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`,
            expandir: `Expande el siguiente texto añadiendo más detalles y contexto relevante. Elimina cualquier tipo de interjección o expresión propia del lenguaje oral (mmm, ahhh, eh, um, etc.) y expresiones de duda cuando se habla o piensa en voz alta:\n\n${text}`
        };

        const model = this.config.postprocessModel || 'gemini-2.0-flash';
        
        // Aplicar configuración según el estilo de respuesta
        let temperature = this.config.temperature || 0.3;
        let topP = this.config.topP || 0.95;
        
        if (this.config.responseStyle === 'factual') {
            temperature = 0.2;
            topP = 0.9;
        } else if (this.config.responseStyle === 'creative') {
            temperature = 0.7;
            topP = 0.95;
        }

        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${this.config.googleApiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contents: [
                    {
                        parts: [
                            {
                                text: `Eres un asistente que ayuda a mejorar textos. Responde únicamente con el texto mejorado, sin explicaciones adicionales.\n\n${prompts[action] || prompts.claridad}`
                            }
                        ]
                    }
                ],
                generationConfig: {
                    temperature: temperature,
                    topP: topP,
                    maxOutputTokens: Math.min(this.config.maxTokens || 1000, 8192) // Gemini max is 8192
                }
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error?.message || `HTTP ${response.status}`);
        }

        const data = await response.json();
        return data.candidates?.[0]?.content?.parts?.[0]?.text || text;
    }
    
    applyAIImprovement(text, action) {
        const mejoras = {
            claridad: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/\s+/g, ' ')
                    .trim() + ' [Text improved for clarity]';
            },
            formal: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/muy/g, 'sumamente')
                    .replace(/bueno/g, 'excelente')
                    .replace(/bien/g, 'de manera adecuada')
                    .replace(/creo que/g, 'considero que') + ' [Versión formal]';
            },
            casual: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/sumamente/g, 'súper')
                    .replace(/excelente/g, 'genial')
                    .replace(/considero que/g, 'creo que') + ' [Versión casual]';
            },
            academico: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/muy/g, 'significativamente')
                    .replace(/bueno/g, 'óptimo')
                    .replace(/creo que/g, 'se puede argumentar que')
                    .replace(/porque/g, 'debido a que') + ' [Versión académica]';
            },
            narrativo: (texto) => {
                return texto
                    .replace(/\b(y entonces|y luego)\b/g, 'después')
                    .replace(/\b(muy)\b/g, 'sumamente')
                    .replace(/\bdijo\b/g, 'murmuró') + ' [Versión narrativa mejorada]';
            },
            academico_v2: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/\s+/g, ' ')
                    .trim() + ' [Mejora académica con cambios mínimos]';
            },
            resumir: (texto) => {
                const words = texto.split(' ');
                const summary = words.slice(0, Math.min(20, words.length)).join(' ');
                return `Resumen: ${summary}${words.length > 20 ? '...' : ''}`;
            },
            expandir: (texto) => {
                return texto + ' [Se han añadido detalles adicionales y contexto relevante para enriquecer el contenido y proporcionar una comprensión más completa del tema tratado.]';
            }
        };
        
        return mejoras[action] ? mejoras[action](text) : text;
    }
    
    // Formato de texto
    applyFormat(format) {
        const editor = document.getElementById('editor');
        editor.focus();
        
        switch (format) {
            case 'bold':
                document.execCommand('bold', false, null);
                break;
            case 'italic':
                document.execCommand('italic', false, null);
                break;
            case 'underline':
                document.execCommand('underline', false, null);
                break;
            case 'ul':
                document.execCommand('insertUnorderedList', false, null);
                break;
            case 'ol':
                document.execCommand('insertOrderedList', false, null);
                break;
            case 'h1':
                this.applyHeaderFormat('h1');
                break;
            case 'h2':
                this.applyHeaderFormat('h2');
                break;
            case 'h3':
                this.applyHeaderFormat('h3');
                break;
        }
        
        this.updateFormatButtons();
        this.handleEditorChange();
    }
    
    applyHeaderFormat(tag) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return;
        
        const range = selection.getRangeAt(0);
        let selectedText = range.toString();
        
        if (selectedText.length === 0) {
            // No text selected, insert placeholder text
            selectedText = 'Título ' + tag.toUpperCase();
        }
        
        // Check if we're already in a header element
        let parentElement = range.commonAncestorContainer;
        if (parentElement.nodeType === Node.TEXT_NODE) {
            parentElement = parentElement.parentElement;
        }
        
        // If already a header, remove the header formatting
        if (parentElement.tagName && parentElement.tagName.toLowerCase().match(/^h[1-6]$/)) {
            const textContent = parentElement.textContent;
            const textNode = document.createTextNode(textContent);
            parentElement.parentNode.replaceChild(textNode, parentElement);
            
            // Restore selection
            const newRange = document.createRange();
            newRange.selectNodeContents(textNode);
            selection.removeAllRanges();
            selection.addRange(newRange);
        } else {
            // Apply header formatting
            const headerElement = document.createElement(tag);
            headerElement.textContent = selectedText;
            
            try {
                range.deleteContents();
                range.insertNode(headerElement);
                
                // Set cursor after the header
                const newRange = document.createRange();
                newRange.setStartAfter(headerElement);
                newRange.collapse(true);
                selection.removeAllRanges();
                selection.addRange(newRange);
            } catch (e) {
                // Fallback: use document.execCommand with formatBlock
                document.execCommand('formatBlock', false, tag);
            }
        }
    }
    
    updateFormatButtons() {
        const formatButtons = document.querySelectorAll('.format-btn');
        formatButtons.forEach(btn => {
            const format = btn.dataset.format;
            let isActive = false;
            
            switch (format) {
                case 'bold':
                    isActive = document.queryCommandState('bold');
                    break;
                case 'italic':
                    isActive = document.queryCommandState('italic');
                    break;
                case 'underline':
                    isActive = document.queryCommandState('underline');
                    break;
                case 'h1':
                case 'h2':
                case 'h3':
                    isActive = this.isInHeaderTag(format);
                    break;
            }
            
            btn.classList.toggle('active', isActive);
        });
    }
    
    isInHeaderTag(headerTag) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return false;
        
        let element = selection.anchorNode;
        if (element.nodeType === Node.TEXT_NODE) {
            element = element.parentElement;
        }
        
        while (element && element !== document.getElementById('editor')) {
            if (element.tagName && element.tagName.toLowerCase() === headerTag) {
                return true;
            }
            element = element.parentElement;
        }
        
        return false;
    }
    
    // Modales y overlays
    showDeleteModal() {
        const modal = document.getElementById('delete-modal');
        modal.classList.add('active');
    }
    
    hideDeleteModal() {
        const modal = document.getElementById('delete-modal');
        modal.classList.remove('active');
    }
    
    showProcessingOverlay(text) {
        const overlay = document.getElementById('processing-overlay');
        const textElement = document.getElementById('processing-text');
        textElement.textContent = text;
        overlay.classList.add('active');
    }
    
    hideProcessingOverlay() {
        const overlay = document.getElementById('processing-overlay');
        overlay.classList.remove('active');
    }
    
    // Notificaciones
    showNotification(message, type = 'success') {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${type === 'success' ? '✓' : type === 'warning' ? '⚠' : 'ℹ'}</span>
                <span class="notification-message">${message}</span>
            </div>
        `;
        
        // Estilos inline para la notificación
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 16px',
            borderRadius: '8px',
            backgroundColor: type === 'success' ? 'var(--color-success)' : 
                           type === 'warning' ? 'var(--color-warning)' : 'var(--color-info)',
            color: 'white',
            fontSize: '14px',
            fontWeight: '500',
            zIndex: '3000',
            opacity: '0',
            transform: 'translateY(-10px)',
            transition: 'all 0.3s ease',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
        });
        
        document.body.appendChild(notification);
        
        // Animar entrada
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateY(0)';
        }, 100);
        
        // Remover después de 3 segundos
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    // Utilidades
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Configuración de listeners para controles avanzados
    setupConfigurationListeners() {
        // Range controls
        const temperatureRange = document.getElementById('temperature-range');
        const topPRange = document.getElementById('top-p-range');
        const responseStyle = document.getElementById('response-style');
        
        if (temperatureRange) {
            temperatureRange.addEventListener('input', () => {
                this.updateRangeValues();
                if (responseStyle.value !== 'custom') {
                    responseStyle.value = 'custom';
                }
            });
        }
        
        if (topPRange) {
            topPRange.addEventListener('input', () => {
                this.updateRangeValues();
                if (responseStyle.value !== 'custom') {
                    responseStyle.value = 'custom';
                }
            });
        }
        
        if (responseStyle) {
            responseStyle.addEventListener('change', (e) => {
                this.applyResponseStylePreset(e.target.value);
            });
        }
    }
    
    updateRangeValues() {
        const temperatureRange = document.getElementById('temperature-range');
        const temperatureValue = document.getElementById('temperature-value');
        const topPRange = document.getElementById('top-p-range');
        const topPValue = document.getElementById('top-p-value');
        
        if (temperatureRange && temperatureValue) {
            temperatureValue.textContent = temperatureRange.value;
        }
        
        if (topPRange && topPValue) {
            topPValue.textContent = topPRange.value;
        }
    }
    
    applyResponseStylePreset(style) {
        const temperatureRange = document.getElementById('temperature-range');
        const topPRange = document.getElementById('top-p-range');
        
        if (!temperatureRange || !topPRange) return;
        
        switch (style) {
            case 'factual':
                temperatureRange.value = '0.2';
                topPRange.value = '0.90';
                break;
            case 'balanced':
                temperatureRange.value = '0.3';
                topPRange.value = '0.95';
                break;
            case 'creative':
                temperatureRange.value = '0.7';
                topPRange.value = '0.95';
                break;
            // 'custom' no hace cambios
        }
        
        this.updateRangeValues();
    }
    
    // Gestión de historial de cambios de IA
    saveAIHistory() {
        const editor = document.getElementById('editor');
        const currentContent = editor.innerHTML;
        
        const historyEntry = {
            content: currentContent,
            timestamp: Date.now(),
            noteId: this.currentNote?.id
        };
        
        this.aiHistory.push(historyEntry);
        
        // Mantener solo los últimos N cambios
        if (this.aiHistory.length > this.maxHistorySize) {
            this.aiHistory.shift();
        }
    }
    
    undoAIChange() {
        if (this.aiHistory.length === 0) {
            this.showNotification('No hay cambios de IA para deshacer', 'warning');
            return;
        }
        
        const lastEntry = this.aiHistory.pop();
        
        // Verificar que estamos en la misma nota
        if (lastEntry.noteId !== this.currentNote?.id) {
            this.showNotification('No se puede deshacer: cambio de nota diferente', 'warning');
            this.aiHistory.length = 0; // Limpiar historial si cambió de nota
            this.updateUndoButton();
            return;
        }
        
        const editor = document.getElementById('editor');
        editor.innerHTML = lastEntry.content;
        
        this.updateUndoButton();
        this.handleEditorChange();
        this.showNotification('Cambio de IA deshecho');
    }
    
    updateUndoButton() {
        const undoBtn = document.getElementById('undo-ai-btn');
        if (undoBtn) {
            undoBtn.disabled = this.aiHistory.length === 0 || 
                              (this.aiHistory.length > 0 && this.aiHistory[this.aiHistory.length - 1].noteId !== this.currentNote?.id);
        }
    }
    
    clearAIHistory() {
        this.aiHistory.length = 0;
        this.updateUndoButton();
    }
}

// Inicializar la aplicación cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    window.notesApp = new NotesApp();
});

// Actualizar botones de formato cuando cambia la selección
document.addEventListener('selectionchange', () => {
    const editor = document.getElementById('editor');
    if (editor && editor.contains(document.getSelection().anchorNode)) {
        // Pequeño delay para que se actualice el estado
        setTimeout(() => {
            if (window.notesApp) {
                window.notesApp.updateFormatButtons();
                window.notesApp.updateSelectedText();
            }
        }, 10);
    }
});

// Manejar atajos de teclado
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
            case 's':
                e.preventDefault();
                if (window.notesApp && window.notesApp.currentNote) {
                    window.notesApp.saveCurrentNote();
                }
                break;
            case 'n':
                e.preventDefault();
                if (window.notesApp) {
                    window.notesApp.createNewNote();
                }
                break;
        }
    }
});

// Configuración modal listeners
window.notesApp.setupConfigurationListeners();