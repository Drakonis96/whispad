// Example data and configuration
const ejemplosTranscripcion = [
    "This is a dictated note about the web development project we are working on in the office.",
    "Team meeting scheduled for tomorrow at 10:00 AM to review quarterly progress.",
    "Ideas to improve user experience in the mobile application we are developing.",
    "Pending tasks list: review code, update documentation, prepare client presentation.",
    "Conference notes on artificial intelligence and its applications in modern web development.",
    "Brainstorming new features to implement in the next version of the application."
];

const configuracionMejoras = {
    claridad: {
        nombre: "Improve Clarity",
        descripcion: "Makes text clearer and more direct",
        icono: "✨",
        prompt: "Rewrite the following text to be clearer, more direct and easier to understand. Keep the same meaning but improve clarity. Remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud:",
        visible: true
    },
    formal: {
        nombre: "Make Formal",
        descripcion: "Converts text to a more formal tone",
        icono: "🎩",
        prompt: "Rewrite the following text using a formal and professional tone, appropriate for an academic or business context. Remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud:",
        visible: false
    },
    casual: {
        nombre: "Make Casual",
        descripcion: "Converts text to a more casual tone",
        icono: "😊",
        prompt: "Rewrite the following text using a casual and friendly tone, as if you were talking to a friend. Remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud:",
        visible: false
    },
    academico: {
        nombre: "Academic",
        descripcion: "Converts text to academic style",
        icono: "🎓",
        prompt: "Rewrite the following text using an academic style with precise terminology, formal structure and appropriate references. Remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud:",
        visible: false
    },
    narrativo: {
        nombre: "Narrative",
        descripcion: "Improves narrative texts and novel dialogues",
        icono: "📖",
        prompt: "Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Improve fluency, description and literary quality while maintaining the essence of the text:",
        visible: false
    },
    academico_v2: {
        nombre: "Academic v2",
        descripcion: "Academic improvement with minimal changes, preserving author's words",
        icono: "🎓",
        prompt: "Improve the following academic text making minimal changes to preserve the author's words. Use more precise words when necessary, improve structure and remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud. Keep the original style and vocabulary as much as possible:",
        visible: true
    },
    resumir: {
        nombre: "Summarize",
        descripcion: "Creates a concise summary of the text",
        icono: "📝",
        prompt: "Create a concise and clear summary of the following text, maintaining the most important points. Remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud:",
        visible: false
    },
    expandir: {
        nombre: "Expand",
        descripcion: "Adds more details and context",
        icono: "✚",
        prompt: "Expand the following text by adding more details, examples and relevant context to enrich the content. Remove any type of interjection or expression typical of oral language (mmm, ahhh, eh, um, etc.) and expressions of doubt when speaking or thinking out loud:",
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
        this.insertionRange = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        
        // History to undo AI changes
        this.aiHistory = [];
        this.maxHistorySize = 10;
        
        // Provider configuration
        this.config = {
            transcriptionProvider: '',
            postprocessProvider: '',
            transcriptionModel: '',
            postprocessModel: '',
            transcriptionLanguage: 'auto', // auto-detectar por defecto
            // Nuevas opciones para GPT-4o transcription
            streamingEnabled: true,
            transcriptionPrompt: '',
            // Configuración avanzada de post-procesamiento
            temperature: 0.3,
            maxTokens: 1000,
            topP: 0.95,
            responseStyle: 'balanced',
            showMobileRecordButton: true
        };
        
        // Visible styles configuration
        this.stylesConfig = { ...configuracionMejoras };

        this.overwrittenFiles = new Set();

        this.selectedTags = new Set();
        
        this.init();
    }
    
    async init() {
        this.loadConfig();
        this.loadStylesConfig();
        await this.loadNotes();
        this.setupEventListeners();
        this.setupConfigurationListeners();
        this.renderNotesList();
        await this.setupDefaultNote();
        this.updateAIButtons();
        
        // Verificar estado del backend
        await this.checkBackendStatus();
        // Sidebar responsive: cerrar en móvil por defecto
        this.setupSidebarResponsive();
        this.setupMobileHeaderActions();
        this.updateMobileFabVisibility();

        // Migrate existing notes without ID
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
                    console.log(`Migrated ${result.migrated_count} notes to new structure`);
                }
            }
        } catch (error) {
            console.log('Error migrating existing notes:', error);
        }
    }
    
    setupSidebarResponsive() {
        const sidebar = document.querySelector('.sidebar');
        const hamburger = document.getElementById('hamburger-menu');
        // Cerrar sidebar por defecto en móvil
        if (window.innerWidth <= 900) {
            sidebar.classList.remove('active');
        }
        // Toggle con hamburguesa
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
        // Cerrar sidebar al hacer click fuera (opcional)
        document.addEventListener('click', (e) => {
            if (window.innerWidth > 900) return;
            if (!sidebar.contains(e.target) && !hamburger.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
        // Opcional: cerrar al cambiar tamaño de pantalla
        window.addEventListener('resize', () => {
            if (window.innerWidth > 900) {
                sidebar.classList.add('active');
            } else {
                sidebar.classList.remove('active');
            }
        });
    }

    setupMobileHeaderActions() {
        const headerActions = document.querySelector('.header-actions');
        const mobileContainer = document.querySelector('.mobile-header-actions');
        const hamburger = document.getElementById('hamburger-menu');
        if (!headerActions || !mobileContainer || !hamburger) return;

        const buttons = Array.from(headerActions.querySelectorAll('button')).filter(btn => btn !== hamburger);

        const moveButtons = () => {
            if (window.innerWidth <= 900) {
                buttons.forEach(btn => mobileContainer.appendChild(btn));
                mobileContainer.style.display = 'flex';
            } else {
                buttons.forEach(btn => headerActions.insertBefore(btn, hamburger));
                mobileContainer.style.display = 'none';
            }
        };

        moveButtons();
        this.updateMobileFabVisibility();
        window.addEventListener('resize', () => {
            moveButtons();
            this.updateMobileFabVisibility();
        });
    }
    
    // Configurar event listeners
    setupEventListeners() {
        // New note button
        document.getElementById('new-note-btn').addEventListener('click', async () => {
            await this.createNewNote();
        });
        
        // Search
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.searchTerm = e.target.value.toLowerCase();
            this.renderNotesList();
        });
        
        // Recording
        document.getElementById('record-btn').addEventListener('click', () => {
            if (!this.isRecording) {
                this.captureInsertionRange();
            }
            this.toggleRecording();
        });
        const mobileFab = document.getElementById('mobile-record-fab');
        if (mobileFab) {
            const handleMobileFab = () => {
                if (!this.isRecording) {
                    this.captureInsertionRange();
                }
                this.toggleRecording();
            };
            mobileFab.addEventListener('click', handleMobileFab);
        }
        
        // Botones de IA - Se configurarán dinámicamente con updateAIButtons()
        // document.querySelectorAll('.ai-btn').forEach(btn => {
        //     btn.addEventListener('click', (e) => {
        //         console.log('AI button clicked:', e.currentTarget.dataset.action);
        //         const action = e.currentTarget.dataset.action;
        //         this.improveText(action);
        //     });
        // });
        
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

        // Show insertion marker on click/touch
        const showMarker = () => {
            this.showInsertionMarker();
        };
        editor.addEventListener('click', showMarker);
        editor.addEventListener('touchend', showMarker);
        
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
        
        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadCurrentNote();
        });
        
        document.getElementById('delete-btn').addEventListener('click', () => {
            this.showDeleteModal();
        });

        document.getElementById('download-all-btn').addEventListener('click', () => {
            this.downloadAllNotes();
        });

        document.getElementById('restore-btn').addEventListener('click', () => {
            this.showRestoreModal();
        });

        document.getElementById('cancel-restore').addEventListener('click', () => {
            this.hideRestoreModal();
        });

        document.getElementById('upload-models-btn').addEventListener('click', () => {
            this.showUploadModelsModal();
        });

        document.getElementById('cancel-upload-models').addEventListener('click', () => {
            this.hideUploadModelsModal();
        });

        this.setupRestoreDropZone();
        this.setupUploadModelsDropZone();
        this.setupDownloadModelButtons();
        
        // Modal de confirmación
        document.getElementById('cancel-delete').addEventListener('click', () => {
            this.hideDeleteModal();
        });
        
        document.getElementById('confirm-delete').addEventListener('click', async () => {
            await this.deleteCurrentNote();
        });
        
        // Configuración
        document.getElementById('config-btn').addEventListener('click', () => {
            this.showConfigModal();
        });
        
        // Styles configuration
        document.getElementById('styles-config-btn').addEventListener('click', () => {
            this.showStylesConfigModal();
        });
        
        document.getElementById('cancel-config').addEventListener('click', () => {
            this.hideConfigModal();
        });
        
        document.getElementById('save-config').addEventListener('click', () => {
            this.saveConfig();
        });
        
        // Listener para cambios en el modelo de transcripción
        document.getElementById('transcription-model').addEventListener('change', () => {
            this.updateTranscriptionOptions();
        });
        
        document.getElementById('cancel-styles-config').addEventListener('click', () => {
            this.hideStylesConfigModal();
        });
        
        document.getElementById('save-styles-config').addEventListener('click', () => {
            this.saveStylesConfig();
        });
        
        // Añadir nuevo estilo
        document.getElementById('add-style-btn').addEventListener('click', () => {
            this.addNewStyle();
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
        
        console.log('Selection updated:', this.selectedText);
        
        if (this.selectedText && selection.rangeCount > 0) {
            this.selectedRange = selection.getRangeAt(0).cloneRange();
            this.insertionRange = this.selectedRange.cloneRange();
            this.updateAIButtonsState(false);
            console.log('Text selected, AI buttons enabled');
        } else {
            this.selectedRange = null;
            this.updateAIButtonsState(true);
            console.log('No text selected, AI buttons disabled');
        }
    }

    // Show a marker where the next transcription will be inserted
    showInsertionMarker() {
        // Remove existing marker
        const oldMarker = document.getElementById('insertion-marker');
        if (oldMarker) oldMarker.remove();

        const selection = window.getSelection();
        if (!selection.rangeCount) return;

        const range = selection.getRangeAt(0).cloneRange();
        range.collapse(true);
        this.insertionRange = range.cloneRange();
        const rect = range.getClientRects()[0];
        if (!rect) return;

        const editorContent = document.querySelector('.editor-content');
        const editorRect = editorContent.getBoundingClientRect();

        const marker = document.createElement('div');
        marker.id = 'insertion-marker';
        marker.className = 'insertion-marker';
        marker.style.top = `${rect.top - editorRect.top + editorContent.scrollTop}px`;
        marker.style.left = `${rect.left - editorRect.left + editorContent.scrollLeft}px`;
        editorContent.appendChild(marker);
    }

    captureInsertionRange() {
        const editor = document.getElementById('editor');
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && editor.contains(selection.getRangeAt(0).startContainer)) {
            this.insertionRange = selection.getRangeAt(0).cloneRange();
        } else if (!this.insertionRange) {
            const range = document.createRange();
            range.selectNodeContents(editor);
            range.collapse(false);
            this.insertionRange = range.cloneRange();
        }
    }

    // Show or hide the editor depending on whether a note is selected
    updateEditorVisibility() {
        const container = document.querySelector('.editor-container');
        if (!container) return;
        if (this.currentNote) {
            container.classList.remove('hidden');
        } else {
            container.classList.add('hidden');
        }
    }
    
    // Actualizar estado de botones de IA
    updateAIButtonsState(disabled) {
        document.querySelectorAll('.ai-btn').forEach(btn => {
            btn.disabled = disabled;
            btn.style.opacity = disabled ? '0.5' : '1';
            
            if (!disabled) {
                // Añadir indicador visual cuando hay texto seleccionado
                btn.style.boxShadow = '0 0 0 2px var(--color-primary)';
                btn.title = btn.title + ' - Texto seleccionado';
            } else {
                // Quitar indicador visual cuando no hay texto seleccionado
                btn.style.boxShadow = '';
                btn.title = btn.title.replace(' - Texto seleccionado', '');
            }
        });
        

    }
    
    // Gestión de notas
    async loadNotes() {
        try {
            const response = await fetch('/api/list-saved-notes');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.notes = data.notes.map(note => ({
                id: note.id || Date.now() + Math.random(),
                filename: note.filename,
                title: note.filename.replace(/\.md$/, ''),
                content: '',
                createdAt: note.created,
                updatedAt: note.modified,
                tags: (note.tags || []).map(t => t.toLowerCase()),
                loaded: false
            }));
            this.renderTagFilter();
       } catch (error) {
            console.error('Error loading notes from server:', error);
            this.notes = [];
        }
    }

    async fetchNoteContent(note) {
        if (!note) return;
        const params = note.id
            ? `?id=${note.id}`
            : `?filename=${encodeURIComponent(note.filename)}`;
        try {
            const response = await fetch(`/api/get-note${params}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            let markdown = data.content || '';

            // Remove metadata section
            const metaIndex = markdown.indexOf('\n---');
            if (metaIndex !== -1) {
                markdown = markdown.substring(0, metaIndex).trim();
            }

            // Extract title from first heading
            const lines = markdown.split(/\r?\n/);
            if (lines.length && /^#\s/.test(lines[0])) {
                note.title = lines.shift().replace(/^#\s*/, '').trim();
            }
            const body = lines.join('\n').trim();

            note.content = this.markdownToHtml(body);
            note.loaded = true;
        } catch (err) {
            console.error('Error loading note content:', err);
            note.content = '';
            note.loaded = true;
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
        const transcriptionLanguage = document.getElementById('transcription-language').value;
        
        // Nuevas opciones para GPT-4o
        const streamingEnabled = document.getElementById('streaming-enabled').checked;
        const transcriptionPrompt = document.getElementById('transcription-prompt').value.trim();
        
        // Configuración avanzada
        const temperature = parseFloat(document.getElementById('temperature-range').value);
        const maxTokens = parseInt(document.getElementById('max-tokens').value);
        const topP = parseFloat(document.getElementById('top-p-range').value);
        const responseStyle = document.getElementById('response-style').value;
        const showMobileRecordButton = document.getElementById('show-mobile-record').checked;

        this.config = {
            ...this.config, // Mantener otras configuraciones como API keys del .env
            transcriptionProvider,
            postprocessProvider,
            transcriptionModel,
            postprocessModel,
            transcriptionLanguage,
            streamingEnabled,
            transcriptionPrompt,
            temperature,
            maxTokens,
            topP,
            responseStyle,
            showMobileRecordButton
        };

        localStorage.setItem('notes-app-config', JSON.stringify(this.config));
        this.updateMobileFabVisibility();
        this.hideConfigModal();
        this.showNotification('Configuration saved');
    }

    showConfigModal() {
        document.getElementById('transcription-provider').value = this.config.transcriptionProvider;
        document.getElementById('postprocess-provider').value = this.config.postprocessProvider;
        document.getElementById('transcription-model').value = this.config.transcriptionModel || '';
        document.getElementById('postprocess-model').value = this.config.postprocessModel || '';
        document.getElementById('transcription-language').value = this.config.transcriptionLanguage || 'auto';
        
        // Nuevas opciones para GPT-4o
        document.getElementById('streaming-enabled').checked = this.config.streamingEnabled !== false; // true por defecto
        document.getElementById('transcription-prompt').value = this.config.transcriptionPrompt || '';
        
        // Configuración avanzada
        document.getElementById('temperature-range').value = this.config.temperature || 0.3;
        document.getElementById('max-tokens').value = this.config.maxTokens || 1000;
        document.getElementById('top-p-range').value = this.config.topP || 0.95;
        document.getElementById('response-style').value = this.config.responseStyle || 'balanced';
        document.getElementById('show-mobile-record').checked = this.config.showMobileRecordButton !== false;
        
        // Actualizar valores mostrados
        this.updateRangeValues();
        
        // Filtrar modelos según el proveedor seleccionado
        this.updateModelOptions();
        
        // Mostrar/ocultar opciones GPT-4o según el modelo seleccionado
        this.updateTranscriptionOptions();

        const modal = document.getElementById('config-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideConfigModal() {
        const modal = document.getElementById('config-modal');
        modal.classList.remove('active');
        this.showMobileFab();
    }
    
    showStylesConfigModal() {
        this.renderStylesConfig();
        const modal = document.getElementById('styles-config-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideStylesConfigModal() {
        const modal = document.getElementById('styles-config-modal');
        modal.classList.remove('active');
        this.showMobileFab();
        
        // Limpiar formulario de nuevo estilo
        document.getElementById('new-style-name').value = '';
        document.getElementById('new-style-icon').value = '';
        document.getElementById('new-style-description').value = '';
        document.getElementById('new-style-prompt').value = '';
    }

    renderStylesConfig() {
        const stylesGrid = document.getElementById('styles-grid');
        stylesGrid.innerHTML = '';

        Object.entries(this.stylesConfig).forEach(([key, style]) => {
            const styleItem = document.createElement('div');
            const isCustomStyle = style.custom === true;
            styleItem.className = `style-config-item ${!style.visible ? 'disabled' : ''} ${isCustomStyle ? 'custom-style' : ''}`;
            
            styleItem.innerHTML = `
                <label class="style-toggle">
                    <input type="checkbox" ${style.visible ? 'checked' : ''} data-style="${key}">
                    <span class="style-toggle-slider"></span>
                </label>
                <div class="style-info">
                    <div class="style-header">
                        <span class="style-icon">${style.icono}</span>
                        <h4 class="style-name">${style.nombre}</h4>
                    </div>
                    <p class="style-description">${style.descripcion}</p>
                    <div class="style-prompt">${style.prompt}</div>
                </div>
                ${isCustomStyle ? `<button class="delete-style-btn" data-style="${key}" title="Eliminar estilo personalizado"><i class="fas fa-times"></i></button>` : ''}
            `;

            // Add event listener for toggle
            const checkbox = styleItem.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (e) => {
                const styleKey = e.target.dataset.style;
                this.stylesConfig[styleKey].visible = e.target.checked;
                styleItem.classList.toggle('disabled', !e.target.checked);
            });

            // Add event listener to delete custom style
            if (isCustomStyle) {
                const deleteBtn = styleItem.querySelector('.delete-style-btn');
                deleteBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.deleteCustomStyle(key);
                });
            }

            stylesGrid.appendChild(styleItem);
        });
    }

    saveStylesConfig() {
        // Guardar configuración en localStorage
        localStorage.setItem('notes-app-styles-config', JSON.stringify(this.stylesConfig));
        
        // Actualizar botones de IA
        this.updateAIButtons();
        
        // Cerrar modal
        this.hideStylesConfigModal();
        
        this.showNotification('Styles configuration saved');
    }

    loadStylesConfig() {
        const saved = localStorage.getItem('notes-app-styles-config');
        if (saved) {
            const savedConfig = JSON.parse(saved);
            
            // Combine saved configuration with default
            Object.keys(this.stylesConfig).forEach(key => {
                if (savedConfig[key] !== undefined) {
                    this.stylesConfig[key] = { ...this.stylesConfig[key], ...savedConfig[key] };
                }
            });
            
            // Add custom styles that are not in the default configuration
            Object.keys(savedConfig).forEach(key => {
                if (!this.stylesConfig[key] && savedConfig[key].custom) {
                    this.stylesConfig[key] = savedConfig[key];
                }
            });
        }
    }

    addNewStyle() {
        const nameInput = document.getElementById('new-style-name');
        const promptInput = document.getElementById('new-style-prompt');
        
        const name = nameInput.value.trim();
        const prompt = promptInput.value.trim();
        
        if (!name || !prompt) {
            this.showNotification('Please complete both fields', 'error');
            return;
        }
        
        // Crear key del estilo basado en el nombre
        const styleKey = name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
        
        // Verificar si ya existe un estilo con este key
        if (this.stylesConfig[styleKey]) {
            this.showNotification('A style with this name already exists', 'error');
            return;
        }
        
        // Crear el nuevo estilo
        const newStyle = {
            nombre: name,
            descripcion: description,
            icono: icon || '✨',
            prompt: prompt,
            visible: true,
            custom: true
        };
        
        // Añadir al objeto de configuración
        this.stylesConfig[styleKey] = newStyle;
        
        // Limpiar formulario
        nameInput.value = '';
        iconInput.value = '';
        descriptionInput.value = '';
        promptInput.value = '';
        
        // Re-render styles configuration
        this.renderStylesConfig();
        
        this.showNotification(`Style "${name}" added successfully`);
    }

    deleteCustomStyle(styleKey) {
        if (confirm('Are you sure you want to delete this custom style?')) {
            delete this.stylesConfig[styleKey];
            this.renderStylesConfig();
            this.showNotification('Style deleted successfully');
        }
    }

    updateAIButtons() {
        const aiControlsContainer = document.querySelector('.ai-controls');
        
        // Remover botones existentes (excepto el botón de deshacer)
        const aiButtons = aiControlsContainer.querySelectorAll('.ai-btn:not(#undo-ai-btn)');
        aiButtons.forEach(btn => btn.remove());
        
        // Recreate buttons based on styles configuration
        const undoBtn = document.getElementById('undo-ai-btn');
        
        Object.entries(this.stylesConfig).forEach(([key, style]) => {
            if (style.visible) {
                const button = document.createElement('button');
                button.className = 'btn btn--secondary btn--sm ai-btn';
                button.setAttribute('data-action', key);
                button.setAttribute('title', style.descripcion);
                button.innerHTML = `
                    <span class="ai-icon">${style.icono}</span>
                    ${style.nombre}
                `;
                
                // Add event listener
                button.addEventListener('click', () => {
                    this.improveText(key);
                });
                
                // Insertar antes del botón de deshacer
                aiControlsContainer.insertBefore(button, undoBtn);
            }
        });
        
        // Actualizar estado de los botones
        this.updateAIButtonsState();
    }
    
    saveToStorage() {
        localStorage.setItem('notes-app-data', JSON.stringify(this.notes));
    }
    
    async createNewNote() {
        const now = new Date();
        const newNote = {
            id: Date.now(),
            title: `Nota ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`,
            content: '',
            createdAt: now.toISOString(),
            updatedAt: now.toISOString(),
            loaded: true // Mark as loaded since it's a new note with empty content
        };
        
        this.notes.unshift(newNote);
        this.saveToStorage();
        this.renderNotesList();
        await this.selectNote(newNote.id);
        
        // Enfocar el título para edición
        setTimeout(() => {
            document.getElementById('note-title').focus();
            document.getElementById('note-title').select();
        }, 100);
    }
    
    async selectNote(noteId) {
        this.currentNote = this.notes.find(note => note.id === noteId);
        if (this.currentNote) {
            if (!this.currentNote.loaded) {
                await this.fetchNoteContent(this.currentNote);
            }
            this.loadNoteToEditor();
            this.updateNoteSelection();
        }
    }
    
    loadNoteToEditor() {
        if (!this.currentNote) return;
        
        document.getElementById('note-title').value = this.currentNote.title;
        document.getElementById('editor').innerHTML = this.currentNote.content;

        this.renderNoteTags(this.currentNote);
        
        // Habilitar botones
        document.getElementById('save-btn').disabled = false;
        document.getElementById('download-btn').disabled = false;
        document.getElementById('delete-btn').disabled = false;
        
        // Restablecer selección
        this.selectedText = '';
        this.selectedRange = null;
        this.updateAIButtonsState(true);
        
        // Limpiar historial de IA al cambiar de nota
        this.clearAIHistory();

        this.updateEditorVisibility();
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

        this.currentNote.loaded = true;
        
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
                    content: this.currentNote.content,
                    tags: this.currentNote.tags || []
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!silent && result.success) {
                console.log(`Note saved to server: ${result.filename}`);
            }
        } catch (error) {
            console.error('Error saving note to server:', error);
            if (!silent) {
                this.showNotification('Error saving note to server', 'error');
            }
        }
    }
    
    async deleteCurrentNote() {
        if (!this.currentNote) return;
        
        // Store the note ID before removing it from the array
        const noteIdToDelete = this.currentNote.id;
        
        this.notes = this.notes.filter(note => note.id !== this.currentNote.id);
        this.saveToStorage();
        this.renderNotesList();
        
        // Delete from server
        this.deleteNoteFromServer(noteIdToDelete);
        
        this.currentNote = null;
        await this.setupDefaultNote();
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
                console.log(`File deleted from server: ${result.filename}`);
            }
        } catch (error) {
            console.error('Error deleting note from server:', error);
        }
    }

    downloadCurrentNote() {
        if (!this.currentNote) return;
        
        const title = document.getElementById('note-title').value.trim() || 'Untitled Note';
        const content = document.getElementById('editor').innerHTML;
        
        // Convertir HTML a Markdown
        const markdownContent = this.htmlToMarkdown(content, title);
        
        // Crear el archivo para descarga
        const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        // Crear elemento de descarga temporal
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.sanitizeFilename(title)}.md`;
        document.body.appendChild(a);
        a.click();
        
        // Limpiar
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Note downloaded successfully');
    }

    async downloadAllNotes() {
        try {
            const response = await fetch('/api/download-all-notes');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'all_notes.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            this.showNotification('All notes downloaded');
        } catch (error) {
            console.error('Error downloading all notes:', error);
            this.showNotification('Error downloading notes', 'error');
        }
    }

    showRestoreModal() {
        const modal = document.getElementById('restore-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideRestoreModal() {
        const modal = document.getElementById('restore-modal');
        modal.classList.remove('active');
        this.showMobileFab();
    }

    showUploadModelsModal() {
        const modal = document.getElementById('upload-model-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideUploadModelsModal() {
        const modal = document.getElementById('upload-model-modal');
        modal.classList.remove('active');
        this.showMobileFab();

        // Reset the progress section
        const progressSection = document.getElementById('upload-progress-section');
        const fileUploadList = document.getElementById('file-upload-list');
        progressSection.style.display = 'none';
        fileUploadList.innerHTML = '';
    }

    setupRestoreDropZone() {
        const dropZone = document.getElementById('restore-drop-zone');
        const fileInput = document.getElementById('restore-file-input');
        if (!dropZone) return;
        ['dragenter', 'dragover'].forEach(evt => {
            dropZone.addEventListener(evt, e => {
                e.preventDefault();
                dropZone.classList.add('highlight');
            });
        });
        ['dragleave', 'drop'].forEach(evt => {
            dropZone.addEventListener(evt, e => {
                e.preventDefault();
                dropZone.classList.remove('highlight');
            });
        });
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            this.handleRestoreFiles(e.dataTransfer.files);
        });
        if (fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', e => {
                this.handleRestoreFiles(e.target.files);
                fileInput.value = '';
            });
        }
    }

    setupUploadModelsDropZone() {
        const dropZone = document.getElementById('upload-model-drop-zone');
        const fileInput = document.getElementById('upload-model-file-input');
        if (!dropZone) return;
        ['dragenter', 'dragover'].forEach(evt => {
            dropZone.addEventListener(evt, e => {
                e.preventDefault();
                dropZone.classList.add('highlight');
            });
        });
        ['dragleave', 'drop'].forEach(evt => {
            dropZone.addEventListener(evt, e => {
                e.preventDefault();
                dropZone.classList.remove('highlight');
            });
        });
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            this.handleModelFiles(e.dataTransfer.files);
        });
        if (fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', e => {
                this.handleModelFiles(e.target.files);
                fileInput.value = '';
            });
        }
    }

    setupDownloadModelButtons() {
        const buttons = document.querySelectorAll('.model-download');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const size = btn.getAttribute('data-size');
                this.handleModelDownload(size);
            });
        });
    }

    async handleRestoreFiles(fileList) {
        const files = Array.from(fileList);
        if (!files.length) return;

        const mdFiles = files.filter(f => f.name.toLowerCase().endsWith('.md') || f.name.toLowerCase().endsWith('.meta'));
        const invalid = files.filter(f => !f.name.toLowerCase().endsWith('.md') && !f.name.toLowerCase().endsWith('.meta'));
        invalid.forEach(f => this.showNotification(`${f.name} rejected`, 'error'));

        this.overwrittenFiles.clear();

        for (const file of mdFiles) {
            try {
                const result = await this.uploadNoteFile(file);
                if (result.success) {
                    if (result.overwritten) {
                        this.overwrittenFiles.add(result.filename);
                        this.showNotification(`${file.name} overwritten`, 'warning');
                    } else {
                        this.showNotification(`${file.name} imported`, 'success');
                    }
                } else {
                    this.showNotification(`Error importing ${file.name}`, 'error');
                }
            } catch (err) {
                console.error('Upload error', err);
                this.showNotification(`Error importing ${file.name}`, 'error');
            }
        }

        await this.loadNotes();
        this.renderNotesList();
    }

    async uploadNoteFile(file) {
        const formData = new FormData();
        formData.append('note', file, file.name);
        const response = await fetch('/api/upload-note', { method: 'POST', body: formData });
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        return await response.json();
    }

    async handleModelFiles(fileList) {
        const files = Array.from(fileList);
        if (!files.length) return;

        const modelFiles = files.filter(f => f.name.toLowerCase().endsWith('.bin'));
        const invalid = files.filter(f => !f.name.toLowerCase().endsWith('.bin'));
        invalid.forEach(f => this.showNotification(`${f.name} rejected`, 'error'));

        if (modelFiles.length === 0) return;

        // Show progress section
        const progressSection = document.getElementById('upload-progress-section');
        const fileUploadList = document.getElementById('file-upload-list');
        progressSection.style.display = 'block';
        fileUploadList.innerHTML = '';

        let allUploadsComplete = true;
        let hasErrors = false;

        for (const file of modelFiles) {
            const fileItem = this.createFileUploadItem(file);
            fileUploadList.appendChild(fileItem);

            try {
                const result = await this.uploadModelFileWithProgress(file, fileItem);
                if (result.success) {
                    this.updateFileUploadStatus(fileItem, 'success', 
                        result.overwritten ? 'Overwritten' : 'Uploaded successfully');
                    if (result.overwritten) {
                        this.showNotification(`${file.name} overwritten`, 'warning');
                    } else {
                        this.showNotification(`${file.name} uploaded`, 'success');
                    }
                } else {
                    hasErrors = true;
                    allUploadsComplete = false;
                    this.updateFileUploadStatus(fileItem, 'error', 'Upload failed');
                    this.showNotification(`Error uploading ${file.name}`, 'error');
                }
            } catch (err) {
                hasErrors = true;
                allUploadsComplete = false;
                console.error('Upload error', err);
                this.updateFileUploadStatus(fileItem, 'error', 
                    err.message || 'Upload failed');
                this.showNotification(`Error uploading ${file.name}`, 'error');
            }
        }

        // Show completion message and force refresh
        if (allUploadsComplete && !hasErrors) {
            this.showUploadCompleteMessage(fileUploadList);
            // Force refresh transcription providers to load new models
            await this.forceRefreshTranscriptionProviders();
        }
    }

    createFileUploadItem(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-upload-item';
        fileItem.innerHTML = `
            <div class="file-upload-header">
                <span class="file-upload-name">${file.name}</span>
                <span class="file-upload-size">${this.formatFileSize(file.size)}</span>
                <span class="file-upload-status">Preparing...</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar"></div>
            </div>
            <div class="progress-percentage">0%</div>
        `;
        return fileItem;
    }

    updateFileUploadStatus(fileItem, status, message) {
        const statusElement = fileItem.querySelector('.file-upload-status');
        const progressBar = fileItem.querySelector('.progress-bar');
        const progressPercentage = fileItem.querySelector('.progress-percentage');
        
        statusElement.textContent = message;
        statusElement.className = `file-upload-status ${status}`;
        
        if (status === 'success') {
            progressBar.style.width = '100%';
            progressBar.className = 'progress-bar complete';
            progressPercentage.textContent = '100%';
        } else if (status === 'error') {
            progressBar.className = 'progress-bar error';
            progressPercentage.textContent = 'Failed';
        }
    }

    showUploadCompleteMessage(container) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'upload-complete-message';
        messageDiv.innerHTML = `
            <i class="fas fa-check-circle message-icon"></i>
            <span class="message-text">All models uploaded successfully! Refreshing providers...</span>
        `;
        container.appendChild(messageDiv);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async forceRefreshTranscriptionProviders() {
        try {
            // Clear any cached provider data
            this.availableTranscriptionProviders = null;
            
            // Reload transcription providers
            try {
                this.availableTranscriptionProviders = await backendAPI.getTranscriptionProviders();
                console.log('Refreshed transcription providers:', this.availableTranscriptionProviders);
            } catch (error) {
                console.error('Error refreshing transcription providers:', error);
                this.availableTranscriptionProviders = { providers: [], default: null };
            }
            
            // Force a hard refresh of the browser to ensure new models are loaded
            setTimeout(() => {
                window.location.reload(true);
            }, 2000);
            
        } catch (error) {
            console.error('Error refreshing transcription providers:', error);
        }
    }

    async uploadModelFileWithProgress(file, fileItem) {
        const formData = new FormData();
        formData.append('model', file, file.name);
        
        const progressBar = fileItem.querySelector('.progress-bar');
        const progressPercentage = fileItem.querySelector('.progress-percentage');
        const statusElement = fileItem.querySelector('.file-upload-status');
        
        // Create an AbortController with a longer timeout for large files
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30 * 60 * 1000); // 30 minutes timeout
        
        try {
            statusElement.textContent = 'Uploading...';
            
            // Create a new XMLHttpRequest for better progress tracking
            const xhr = new XMLHttpRequest();
            
            return new Promise((resolve, reject) => {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressBar.style.width = percentComplete + '%';
                        progressPercentage.textContent = Math.round(percentComplete) + '%';
                        
                        if (percentComplete < 100) {
                            statusElement.textContent = `Uploading... ${Math.round(percentComplete)}%`;
                        } else {
                            statusElement.textContent = 'Processing...';
                        }
                    }
                });
                
                xhr.addEventListener('load', () => {
                    clearTimeout(timeoutId);
                    if (xhr.status === 200) {
                        try {
                            const result = JSON.parse(xhr.responseText);
                            resolve(result);
                        } catch (e) {
                            reject(new Error('Invalid response format'));
                        }
                    } else {
                        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
                    }
                });
                
                xhr.addEventListener('error', () => {
                    clearTimeout(timeoutId);
                    reject(new Error('Network error during upload'));
                });
                
                xhr.addEventListener('abort', () => {
                    clearTimeout(timeoutId);
                    reject(new Error('Upload timeout - file too large or connection too slow'));
                });
                
                xhr.open('POST', '/api/upload-model');
                xhr.send(formData);
            });
            
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    async uploadModelFile(file) {
        const formData = new FormData();
        formData.append('model', file, file.name);
        
        // Create an AbortController with a longer timeout for large files
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30 * 60 * 1000); // 30 minutes timeout
        
        try {
            const response = await fetch('/api/upload-model', { 
                method: 'POST', 
                body: formData,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Upload timeout - file too large or connection too slow');
            }
            throw error;
        }
    }

    async downloadModelWithProgress(size, fileItem) {
        try {
            const streamResponse = await backendAPI.downloadModelStream(size);
            await backendAPI.processDownloadStream(streamResponse, percent => {
                const progressBar = fileItem.querySelector('.progress-bar');
                const progressPercentage = fileItem.querySelector('.progress-percentage');
                progressBar.style.width = percent + '%';
                progressPercentage.textContent = percent + '%';
                fileItem.querySelector('.file-upload-status').textContent = `Downloading... ${percent}%`;
            });
            this.updateFileUploadStatus(fileItem, 'success', 'Downloaded successfully');
        } catch (error) {
            console.error('Download error', error);
            this.updateFileUploadStatus(fileItem, 'error', 'Download failed');
            throw error;
        }
    }

    async handleModelDownload(size) {
        const progressSection = document.getElementById('upload-progress-section');
        const fileUploadList = document.getElementById('file-upload-list');
        progressSection.style.display = 'block';
        fileUploadList.innerHTML = '';

        const filename = `ggml-${size}.bin`;
        const fileItem = this.createFileUploadItem({ name: filename, size: 0 });
        fileUploadList.appendChild(fileItem);

        try {
            await this.downloadModelWithProgress(size, fileItem);
            this.showUploadCompleteMessage(fileUploadList);
            await this.forceRefreshTranscriptionProviders();
        } catch (err) {
            this.showNotification(`Error downloading ${filename}`, 'error');
        }
    }

    htmlToMarkdown(html, title) {
        // Crear un elemento temporal para procesar el HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        let markdown = `# ${title}\n\n`;
        
        // Procesar cada nodo del HTML
        const content = this.processNode(tempDiv);
        
        // Si no hay contenido, añadir un mensaje
        if (!content.trim()) {
            markdown += '*Esta nota está vacía*\n';
        } else {
            markdown += content;
        }
        
        return markdown.trim();
    }

    markdownToHtml(markdown) {
        if (!markdown) return '';

        const lines = markdown.split(/\r?\n/);
        let html = '';
        let inUl = false;
        let inOl = false;

        const closeLists = () => {
            if (inUl) { html += '</ul>'; inUl = false; }
            if (inOl) { html += '</ol>'; inOl = false; }
        };

        for (let line of lines) {
            if (/^\s*-\s+/.test(line)) {
                if (!inUl) { closeLists(); html += '<ul>'; inUl = true; }
                html += `<li>${line.replace(/^\s*-\s+/, '')}</li>`;
                continue;
            }
            if (/^\s*\d+\.\s+/.test(line)) {
                if (!inOl) { closeLists(); html += '<ol>'; inOl = true; }
                html += `<li>${line.replace(/^\s*\d+\.\s+/, '')}</li>`;
                continue;
            }

            closeLists();

            if (/^######\s+/.test(line)) { html += `<h6>${line.replace(/^######\s+/, '')}</h6>`; continue; }
            if (/^#####\s+/.test(line)) { html += `<h5>${line.replace(/^#####\s+/, '')}</h5>`; continue; }
            if (/^####\s+/.test(line)) { html += `<h4>${line.replace(/^####\s+/, '')}</h4>`; continue; }
            if (/^###\s+/.test(line)) { html += `<h3>${line.replace(/^###\s+/, '')}</h3>`; continue; }
            if (/^##\s+/.test(line)) { html += `<h2>${line.replace(/^##\s+/, '')}</h2>`; continue; }
            if (/^#\s+/.test(line)) { html += `<h1>${line.replace(/^#\s+/, '')}</h1>`; continue; }

            if (line.trim() === '') {
                html += '<br>';
            } else {
                let processed = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
                processed = processed.replace(/\*(.+?)\*/g, '<em>$1</em>');
                html += `<p>${processed}</p>`;
            }
        }
        closeLists();
        return html;
    }

    processNode(node) {
        let result = '';
        
        for (let child of node.childNodes) {
            if (child.nodeType === Node.TEXT_NODE) {
                const text = child.textContent.trim();
                if (text) {
                    result += text;
                }
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                const tagName = child.tagName.toLowerCase();
                const content = this.processNode(child);
                
                switch (tagName) {
                    case 'h1':
                        if (content.trim()) result += `# ${content.trim()}\n\n`;
                        break;
                    case 'h2':
                        if (content.trim()) result += `## ${content.trim()}\n\n`;
                        break;
                    case 'h3':
                        if (content.trim()) result += `### ${content.trim()}\n\n`;
                        break;
                    case 'h4':
                        if (content.trim()) result += `#### ${content.trim()}\n\n`;
                        break;
                    case 'h5':
                        if (content.trim()) result += `##### ${content.trim()}\n\n`;
                        break;
                    case 'h6':
                        if (content.trim()) result += `###### ${content.trim()}\n\n`;
                        break;
                    case 'strong':
                    case 'b':
                        if (content.trim()) result += `**${content.trim()}**`;
                        break;
                    case 'em':
                    case 'i':
                        if (content.trim()) result += `*${content.trim()}*`;
                        break;
                    case 'u':
                        if (content.trim()) result += `<u>${content.trim()}</u>`;
                        break;
                    case 'p':
                        if (content.trim()) result += `${content.trim()}\n\n`;
                        break;
                    case 'br':
                        result += '\n';
                        break;
                    case 'ul':
                        const ulContent = this.processListItems(child, '-');
                        if (ulContent.trim()) result += ulContent + '\n';
                        break;
                    case 'ol':
                        const olContent = this.processListItems(child, '1.');
                        if (olContent.trim()) result += olContent + '\n';
                        break;
                    case 'li':
                        // Los li se procesan en processListItems
                        result += content;
                        break;
                    case 'div':
                        if (content.trim()) result += `${content.trim()}\n`;
                        break;
                    default:
                        result += content;
                        break;
                }
            }
        }
        
        return result;
    }

    processListItems(listElement, marker) {
        let result = '';
        let counter = 1;
        
        for (let child of listElement.children) {
            if (child.tagName.toLowerCase() === 'li') {
                const content = this.processNode(child).trim();
                if (content) {
                    if (marker === '1.') {
                        result += `${counter}. ${content}\n`;
                        counter++;
                    } else {
                        result += `- ${content}\n`;
                    }
                }
            }
        }
        
        return result;
    }


    gatherAllTags() {
        const set = new Set();
        this.notes.forEach(n => (n.tags || []).forEach(t => set.add(t)));
        return Array.from(set).sort();
    }

    renderTagFilter() {
        const container = document.getElementById('tag-filter-bar');
        if (!container) return;
        const tags = this.gatherAllTags();
        container.innerHTML = tags.map(tag => `<span class="tag-badge" data-tag="${tag}">${tag}</span>`).join('');
        container.querySelectorAll('.tag-badge').forEach(badge => {
            const tag = badge.dataset.tag;
            if (this.selectedTags.has(tag)) badge.classList.add('active');
            badge.addEventListener('click', () => {
                if (this.selectedTags.has(tag)) {
                    this.selectedTags.delete(tag);
                    badge.classList.remove('active');
                } else {
                    this.selectedTags.add(tag);
                    badge.classList.add('active');
                }
                this.renderNotesList();
            });
        });
        container.style.display = tags.length ? 'flex' : 'none';
    }

    renderNoteTags(note) {
        const container = document.getElementById('note-tags');
        if (!container) return;
        const tags = (note && note.tags) ? note.tags : [];
        container.innerHTML = tags.map(t => `<span class="tag-badge" data-tag="${t}">${t}<span class="remove-tag" data-tag="${t}">&times;</span></span>`).join('');
        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'tag-input';
        input.className = 'tag-input';
        input.placeholder = 'Add tag...';
        container.appendChild(input);

        container.querySelectorAll('.remove-tag').forEach(btn => {
            const tag = btn.dataset.tag;
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeTag(tag);
            });
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ';' || e.key === ',') {
                e.preventDefault();
                const val = input.value.trim().toLowerCase();
                if (val) {
                    this.addTag(val);
                }
                input.value = '';
            }
        });

        input.addEventListener('blur', () => {
            const val = input.value.trim().toLowerCase();
            if (val) {
                this.addTag(val);
            }
            input.value = '';
        });
    }

    addTag(tag) {
        if (!this.currentNote) return;
        if (!this.currentNote.tags) this.currentNote.tags = [];
        tag = tag.toLowerCase();
        if (!this.currentNote.tags.includes(tag)) {
            this.currentNote.tags.push(tag);
            this.renderNoteTags(this.currentNote);
            this.renderTagFilter();
        }
    }

    removeTag(tag) {
        if (!this.currentNote || !this.currentNote.tags) return;
        this.currentNote.tags = this.currentNote.tags.filter(t => t !== tag);
        this.renderNoteTags(this.currentNote);
        this.renderTagFilter();
    }

    sanitizeFilename(filename) {
        // Remover caracteres no válidos para nombres de archivo
        return filename.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_');
    }
    
    async setupDefaultNote() {
        // Do not auto select any note. Keep the editor hidden until the user
        // chooses one.
        document.getElementById('note-title').value = '';
        document.getElementById('editor').innerHTML = '';
        document.getElementById('save-btn').disabled = true;
        document.getElementById('download-btn').disabled = true;
        document.getElementById('delete-btn').disabled = true;
        this.currentNote = null;
        this.updateEditorVisibility();
    }
    
    // Renderizado de lista
    renderNotesList() {
        const container = document.getElementById('notes-list');
        
        let filteredNotes = this.notes;
        if (this.searchTerm) {
            filteredNotes = filteredNotes.filter(note =>
                note.title.toLowerCase().includes(this.searchTerm) ||
                note.content.toLowerCase().includes(this.searchTerm)
            );
        }

        if (this.selectedTags.size > 0) {
            filteredNotes = filteredNotes.filter(note => {
                const tags = note.tags || [];
                return [...this.selectedTags].every(t => tags.includes(t));
            });
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
            const overwriteCls = this.overwrittenFiles.has(note.filename) ? ' overwritten' : '';

            return `
                <div class="note-item fade-in${overwriteCls}" data-note-id="${note.id}">
                    <div class="note-item-title">${note.title}</div>
                    <div class="note-item-preview">${preview}</div>
                    <div class="note-item-date">${date}</div>
                </div>
            `;
        }).join('');
        
        // Agregar event listeners a los items
        container.querySelectorAll('.note-item').forEach(item => {
            item.addEventListener('click', async () => {
                const noteId = parseInt(item.dataset.noteId);
                await this.selectNote(noteId);
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
            // Verificar que el backend esté disponible
            const backendAvailable = await this.checkBackendStatus();
            if (!backendAvailable) {
                return;
            }
            
            // Verificar que las APIs necesarias estén configuradas en el backend
            if (this.config.transcriptionProvider === 'openai' && !this.availableAPIs?.openai) {
                this.showNotification('OpenAI API not configured in backend', 'warning');
                return;
            }
            
            if (this.config.transcriptionProvider === 'local' && 
                (!this.availableTranscriptionProviders?.providers || 
                 !this.availableTranscriptionProviders.providers.some(p => p.id === 'local'))) {
                this.showNotification('Local whisper.cpp not available in backend', 'warning');
                return;
            }

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Try to use a compatible audio format for MediaRecorder
            let mimeType = 'audio/wav';
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                mimeType = 'audio/webm;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/webm')) {
                mimeType = 'audio/webm';
            } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
                mimeType = 'audio/ogg;codecs=opus';
            }
            
            console.log('Using MediaRecorder with MIME type:', mimeType);
            this.mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType });
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: mimeType });
                await this.transcribeAudio(audioBlob);
                
                // Stop stream
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            
            const recordBtn = document.getElementById('record-btn');
            const recordIcon = document.getElementById('record-icon');
            const recordText = document.getElementById('record-text');
            const mobileFab = document.getElementById('mobile-record-fab');
            const recordingStatus = document.getElementById('recording-status');
            const recordingIndicator = document.getElementById('recording-indicator');
            
            recordBtn.classList.add('btn--error');
            recordIcon.className = 'fas fa-stop';
            recordText.textContent = 'Stop';
            if (mobileFab) {
                mobileFab.classList.add('btn--error');
                mobileFab.innerHTML = '<i class="fas fa-stop"></i>';
            }
            recordingStatus.querySelector('.status-text').textContent = 'Recording...';
            recordingIndicator.classList.add('active');

        } catch (error) {
            console.error('Error accessing microphone:', error);
            this.showNotification('Error accessing microphone', 'error');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            const recordBtn = document.getElementById('record-btn');
            const recordIcon = document.getElementById('record-icon');
            const recordText = document.getElementById('record-text');
            const mobileFab = document.getElementById('mobile-record-fab');
            const recordingStatus = document.getElementById('recording-status');
            const recordingIndicator = document.getElementById('recording-indicator');
            
            recordBtn.classList.remove('btn--error');
            recordIcon.className = 'fas fa-microphone';
            recordText.textContent = 'Record';
            if (mobileFab) {
                mobileFab.classList.remove('btn--error');
                mobileFab.innerHTML = '<i class="fas fa-microphone"></i>';
            }
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
            } else if (this.config.transcriptionProvider === 'local') {
                transcription = await this.transcribeWithLocal(audioBlob);
            } else if (this.config.transcriptionProvider === 'google') {
                // TODO: Implementar Google Speech-to-Text
                transcription = 'Transcripción con Google (no implementado aún)';
            }
            
            if (transcription) {
                this.insertTranscription(transcription);
                this.showNotification('Transcription completed');
            }
            
        } catch (error) {
            console.error('Error in transcription:', error);
            this.showNotification('Error transcribing audio: ' + error.message, 'error');
        } finally {
            this.hideProcessingOverlay();
            document.getElementById('recording-status').querySelector('.status-text').textContent = 'Ready to record';
        }
    }

    async transcribeWithOpenAI(audioBlob) {
        try {
            const model = this.config.transcriptionModel;
            
            // Usar el método unificado para todos los modelos
            console.log('🎯 Using unified transcription');
            console.log('Model:', model);
            console.log('Language:', this.config.transcriptionLanguage);
            
            return await backendAPI.transcribeAudio(
                audioBlob, 
                this.config.transcriptionLanguage, 
                model
            );
        } catch (error) {
            throw new Error(`Error en transcripción: ${error.message}`);
        }
    }

    async transcribeWithLocal(audioBlob) {
        try {
            console.log('🎯 Using local whisper.cpp transcription');
            console.log('Language:', this.config.transcriptionLanguage);
            
            const result = await backendAPI.transcribeAudio(
                audioBlob,
                this.config.transcriptionLanguage,
                this.config.transcriptionModel,
                'local'
            );
            
            console.log('Local transcription result:', result);
            console.log('Transcription text:', result);
            console.log('Transcription length:', result ? result.length : 0);
            
            // Check if we got empty or invalid result
            if (!result || result.trim() === '') {
                throw new Error('Empty transcription result from local whisper.cpp');
            }
            
            return result;
        } catch (error) {
            console.error('Error in local transcription:', error);
            throw new Error(`Error en transcripción local: ${error.message}`);
        }
    }

    async handleStreamingTranscription(audioBlob, options) {
        try {
            this.showProcessingOverlay('Iniciando transcripción en tiempo real...');
            
            // Añadir indicador de streaming en el estado de grabación
            const statusElement = document.getElementById('recording-status').querySelector('.status-text');
            const originalText = statusElement.textContent;
            statusElement.innerHTML = originalText + ' <span class="streaming-indicator active"></span>';
            
            const streamResponse = await backendAPI.transcribeAudioGPT4O(audioBlob, options);
            
            let fullTranscription = '';
            let currentTranscriptionElement = null;
            
            // Crear elemento temporal para mostrar la transcripción en tiempo real
            const editor = document.getElementById('editor');
            const tempElement = document.createElement('span');
            tempElement.className = 'streaming-transcription';
            
            // Obtener posición actual del cursor o insertar al final
            const selection = window.getSelection();
            let range;
            
            if (selection.rangeCount > 0) {
                range = selection.getRangeAt(0);
            } else {
                range = document.createRange();
                range.selectNodeContents(editor);
                range.collapse(false);
            }
            
            // Insertar elemento temporal en la posición del cursor
            range.insertNode(tempElement);
            
            const result = await backendAPI.processStreamingTranscription(
                streamResponse,
                (chunk, fullText) => {
                    // Actualizar overlay con progreso
                    this.showProcessingOverlay(`Transcribing... ${fullText.length} characters`);
                    console.log('Chunk received:', chunk);
                    
                    // Actualizar elemento temporal con el texto completo
                    tempElement.textContent = fullText;
                    
                    // Hacer scroll para mostrar el texto
                    tempElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                },
                (finalText) => {
                    // Completado
                    fullTranscription = finalText;
                    console.log('Transcription complete:', finalText);
                    
                    // Remover elemento temporal
                    if (tempElement.parentNode) {
                        tempElement.parentNode.removeChild(tempElement);
                    }
                }
            );
            
            // Remover indicador de streaming
            statusElement.textContent = originalText;
            
            return fullTranscription || result;
        } catch (error) {
            // Limpiar indicadores en caso de error
            const statusElement = document.getElementById('recording-status').querySelector('.status-text');
            statusElement.textContent = 'Error en transcripción';
            
            // Remover elemento temporal si existe
            const tempElement = document.querySelector('.streaming-transcription');
            if (tempElement && tempElement.parentNode) {
                tempElement.parentNode.removeChild(tempElement);
            }
            
            throw error;
        }
    }

    insertTranscription(transcription) {
        console.log('Inserting transcription:', transcription);
        console.log('Transcription type:', typeof transcription);
        console.log('Transcription length:', transcription ? transcription.length : 0);
        
        if (!transcription || transcription.trim() === '') {
            console.error('Empty transcription received, not inserting');
            this.showNotification('Empty transcription received', 'error');
            return;
        }
        
        const editor = document.getElementById('editor');
        
        // Enfocar el editor
        editor.focus();
        
        // Obtener posición del cursor o insertar al final
        const selection = window.getSelection();
        let range;

        if (selection.rangeCount > 0) {
            range = selection.getRangeAt(0);
            this.insertionRange = range.cloneRange();
        } else if (this.insertionRange) {
            range = this.insertionRange.cloneRange();
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
        this.insertionRange = range.cloneRange();

        // Remove insertion marker after inserting text
        const marker = document.getElementById('insertion-marker');
        if (marker) marker.remove();

        // Disparar evento de cambio
        this.handleEditorChange();
        
        console.log('Transcription inserted successfully');
    }
    
    // Mejora con IA
    async improveText(action) {
        console.log('improveText called with action:', action);
        console.log('selectedText:', this.selectedText);
        console.log('selectedRange:', this.selectedRange);
        
        // Verificar si hay texto seleccionado
        if (!this.selectedText || !this.selectedRange) {
            console.log('No text selected, showing notification');
            this.showNotification('⚠️ Please select text to improve with AI', 'warning');
            
            // Resaltar visualmente los botones de IA para indicar que necesita selección
            document.querySelectorAll('.ai-btn').forEach(btn => {
                btn.style.animation = 'shake 0.5s ease-in-out';
            });
            
            // Quitar animación después de un tiempo
            setTimeout(() => {
                document.querySelectorAll('.ai-btn').forEach(btn => {
                    btn.style.animation = '';
                });
            }, 500);
            
            return;
        }

        // Verificar configuración según el modelo seleccionado
        const provider = this.config.postprocessProvider;
        const model = this.config.postprocessModel;
        const isGemini = provider === 'google';
        const isOpenAI = provider === 'openai';
        const isOpenRouter = provider === 'openrouter';

        // Verificar que el backend esté disponible
        const backendAvailable = await this.checkBackendStatus();
        if (!backendAvailable) {
            return;
        }

        if (isOpenAI && !this.availableAPIs?.openai) {
            this.showNotification('OpenAI API not configured in backend', 'warning');
            return;
        }

        if (isGemini && !this.availableAPIs?.google) {
            this.showNotification('Google API not configured in backend', 'warning');
            this.showConfigModal();
            return;
        }

        if (isOpenRouter && !this.availableAPIs?.openrouter) {
            this.showNotification('OpenRouter API not configured in backend', 'warning');
            this.showConfigModal();
            return;
        }

        // Guardar estado actual para poder deshacer
        this.saveAIHistory();

        this.showProcessingOverlay(`Improving text with AI...`);
        
        try {
            let improvedText = '';
            
            // Guardar información importante antes de modificar el DOM
            const textToImprove = this.selectedText;
            const rangeToReplace = this.selectedRange.cloneRange();
            
            // Crear un elemento span temporal para el streaming con estilo visual
            const tempSpan = document.createElement('span');
            tempSpan.className = 'ai-generating-text';
            tempSpan.style.padding = '2px 4px';
            tempSpan.style.borderRadius = '3px';
            tempSpan.style.border = '1px dashed #1976d2';
            tempSpan.textContent = '⏳ Mejorando...';
            
            // Reemplazar el texto seleccionado con el elemento temporal
            rangeToReplace.deleteContents();
            rangeToReplace.insertNode(tempSpan);
            
            // Limpiar selección visual pero mantener referencia
            const selection = window.getSelection();
            selection.removeAllRanges();
            // NO limpiar selectedText y selectedRange hasta completar el proceso
            this.updateAIButtonsState(true);
            
            if (isOpenAI) {
                improvedText = await this.improveWithOpenAIStream(textToImprove, action, tempSpan);
            } else if (isGemini) {
                improvedText = await this.improveWithGeminiStream(textToImprove, action, tempSpan);
            } else if (isOpenRouter) {
                improvedText = await this.improveWithOpenRouterStream(textToImprove, action, tempSpan);
            } else {
                // Fallback a mejora local
                improvedText = this.applyAIImprovement(textToImprove, action);
                // Para el fallback, simular el proceso de generación
                tempSpan.className = 'ai-generating-text';
                tempSpan.textContent = improvedText;
                
                // Después de un momento, cambiar a texto completado
                setTimeout(() => {
                    tempSpan.className = 'ai-generated-text';
                    setTimeout(() => {
                        tempSpan.className = '';
                    }, 1000);
                }, 500);
            }
            
            // Quitar estilos visuales del elemento temporal al finalizar
            tempSpan.className = 'ai-generated-text';
            tempSpan.style.border = '';
            tempSpan.style.padding = '';
            tempSpan.style.borderRadius = '';
            
            // Después de un breve delay, remover completamente las clases de IA
            setTimeout(() => {
                tempSpan.className = '';
            }, 1000);
            
            // Limpiar variables de selección ahora que terminamos
            this.selectedText = '';
            this.selectedRange = null;
            
            // Habilitar botón de deshacer
            this.updateUndoButton();
            
            this.hideProcessingOverlay();
            this.showNotification(`Text improved: ${configuracionMejoras[action].nombre}`);
            this.handleEditorChange();
            
        } catch (error) {
            this.hideProcessingOverlay();
            console.error('Error improving text:', error);
            
            // Restaurar el texto original si algo falló
            if (tempSpan && tempSpan.parentNode) {
                tempSpan.textContent = textToImprove;
                tempSpan.className = '';
                tempSpan.style.backgroundColor = '#ffebee';
                tempSpan.style.color = '#c62828';
            }
            
            // Limpiar variables de selección
            this.selectedText = '';
            this.selectedRange = null;
            
            this.showNotification('Error improving text: ' + error.message, 'error');
        }
    }

    async improveWithOpenAI(text, action) {
        try {
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            // Usar el backend en lugar de la API directamente
            return await backendAPI.improveText(text, action, 'openai', false, null, customPrompt);
        } catch (error) {
            throw new Error(`Error improving text with OpenAI: ${error.message}`);
        }
    }

    async improveWithOpenAIStream(text, action, tempElement) {
        try {
            console.log('Starting OpenAI stream for action:', action);
            
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            const response = await backendAPI.improveText(text, action, 'openai', true, null, customPrompt);
            
            if (!response.body) {
                throw new Error('No response body received');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let improvedText = '';
            let chunkCount = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('Stream completed. Total chunks:', chunkCount);
                    break;
                }
                
                chunkCount++;
                const chunk = decoder.decode(value);
                console.log('Received chunk:', chunkCount, chunk);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') {
                                console.log('Received [DONE] signal');
                                break;
                            }
                            
                            const data = JSON.parse(dataStr);
                            console.log('Parsed data:', data);
                            
                            if (data.content) {
                                improvedText += data.content;
                                // Limpiar y actualizar el texto en tiempo real
                                const cleanedText = this.cleanAIResponse(improvedText);
                                tempElement.textContent = cleanedText;
                                console.log('Updated temp element with:', cleanedText.substring(0, 50) + '...');
                                
                                // Mantener la clase de generación durante el streaming
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('Stream marked as done');
                                // Asegurar que el texto final esté limpio
                                const finalText = this.cleanAIResponse(improvedText);
                                tempElement.textContent = finalText;
                                console.log('Final text set:', finalText);
                                
                                // Cambiar a clase de texto completado
                                tempElement.className = 'ai-generated-text';
                                
                                // Después de la transición, quitar todas las clases
                                setTimeout(() => {
                                    tempElement.className = '';
                                }, 1000);
                                
                                return finalText;
                            }
                            if (data.error) {
                                console.error('Error in stream data:', data.error);
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse JSON:', parseError, 'Line:', line);
                            // Ignorar errores de parsing de JSON
                            continue;
                        }
                    }
                }
            }
            
            const finalResult = this.cleanAIResponse(improvedText);
            console.log('Returning final result:', finalResult);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithOpenAIStream:', error);
            throw new Error(`Error improving text with OpenAI: ${error.message}`);
        }
    }

    async improveWithGemini(text, action) {
        try {
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            // Usar el backend en lugar de la API directamente
            return await backendAPI.improveText(text, action, 'google', false, null, customPrompt);
        } catch (error) {
            throw new Error(`Error improving text with Gemini: ${error.message}`);
        }
    }

    async improveWithGeminiStream(text, action, tempElement) {
        try {
            console.log('Starting Gemini stream for action:', action);
            
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            const response = await backendAPI.improveText(text, action, 'google', true, null, customPrompt);
            
            if (!response.body) {
                throw new Error('No response body received');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let improvedText = '';
            let chunkCount = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('Gemini stream completed. Total chunks:', chunkCount);
                    break;
                }
                
                chunkCount++;
                const chunk = decoder.decode(value);
                console.log('Received Gemini chunk:', chunkCount, chunk);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6).trim();
                            const data = JSON.parse(dataStr);
                            console.log('Parsed Gemini data:', data);
                            
                            if (data.content) {
                                improvedText += data.content;
                                // Limpiar y actualizar el texto en tiempo real
                                const cleanedText = this.cleanAIResponse(improvedText);
                                tempElement.textContent = cleanedText;
                                console.log('Updated Gemini temp element with:', cleanedText.substring(0, 50) + '...');
                                
                                // Mantener la clase de generación durante el streaming
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('Gemini stream marked as done');
                                // Asegurar que el texto final esté limpio
                                const finalText = this.cleanAIResponse(improvedText);
                                tempElement.textContent = finalText;
                                console.log('Final Gemini text set:', finalText);
                                
                                // Cambiar a clase de texto completado
                                tempElement.className = 'ai-generated-text';
                                
                                // Después de la transición, quitar todas las clases
                                setTimeout(() => {
                                    tempElement.className = '';
                                }, 1000);
                                
                                return finalText;
                            }
                            if (data.error) {
                                console.error('Error in Gemini stream data:', data.error);
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse Gemini JSON:', parseError, 'Line:', line);
                            // Ignorar errores de parsing de JSON
                            continue;
                        }
                    }
                }
            }
            
            const finalResult = this.cleanAIResponse(improvedText);
            console.log('Returning final Gemini result:', finalResult);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithGeminiStream:', error);
            throw new Error(`Error improving text with Gemini: ${error.message}`);
        }
    }
    
    async improveWithOpenRouter(text, action) {
        try {
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            const model = this.config.postprocessModel;
            return await backendAPI.improveText(text, action, 'openrouter', false, model, customPrompt);
        } catch (error) {
            throw new Error(`Error improving text with OpenRouter: ${error.message}`);
        }
    }

    async improveWithOpenRouterStream(text, action, tempElement) {
        try {
            console.log('Starting OpenRouter stream for action:', action);
            
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            const model = this.config.postprocessModel;
            const response = await backendAPI.improveText(text, action, 'openrouter', true, model, customPrompt);
            
            if (!response.body) {
                throw new Error('No response body received');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let improvedText = '';
            let chunkCount = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('OpenRouter stream completed. Total chunks:', chunkCount);
                    break;
                }
                
                chunkCount++;
                const chunk = decoder.decode(value);
                console.log('Received OpenRouter chunk:', chunkCount, chunk);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') {
                                console.log('Received OpenRouter [DONE] signal');
                                break;
                            }
                            
                            const data = JSON.parse(dataStr);
                            console.log('Parsed OpenRouter data:', data);
                            
                            if (data.content) {
                                improvedText += data.content;
                                // Limpiar y actualizar el texto en tiempo real
                                const cleanedText = this.cleanAIResponse(improvedText);
                                tempElement.textContent = cleanedText;
                                console.log('Updated OpenRouter temp element with:', cleanedText.substring(0, 50) + '...');
                                
                                // Mantener la clase de generación durante el streaming
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('OpenRouter stream marked as done');
                                // Asegurar que el texto final esté limpio
                                const finalText = this.cleanAIResponse(improvedText);
                                tempElement.textContent = finalText;
                                console.log('Final OpenRouter text set:', finalText);
                                
                                // Cambiar a clase de texto completado
                                tempElement.className = 'ai-generated-text';
                                
                                // Después de la transición, quitar todas las clases
                                setTimeout(() => {
                                    tempElement.className = '';
                                }, 1000);
                                
                                return finalText;
                            }
                            if (data.error) {
                                console.error('Error in OpenRouter stream data:', data.error);
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse OpenRouter JSON:', parseError, 'Line:', line);
                            // Ignorar errores de parsing de JSON
                            continue;
                        }
                    }
                }
            }
            
            const finalResult = this.cleanAIResponse(improvedText);
            console.log('Returning final OpenRouter result:', finalResult);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithOpenRouterStream:', error);
            throw new Error(`Error improving text with OpenRouter: ${error.message}`);
        }
    }
    
    // Clean AI response to ensure it only returns the edited text
    cleanAIResponse(text) {
        if (!text || typeof text !== 'string') {
            console.warn('cleanAIResponse received invalid text:', text);
            return '';
        }
        
        // Quitar comillas si envuelven todo el texto
        let cleaned = text.trim();
        
        // Si está entre comillas dobles, quitarlas
        if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
            cleaned = cleaned.slice(1, -1);
        }
        
        // Si está entre comillas simples, quitarlas
        if (cleaned.startsWith("'") && cleaned.endsWith("'")) {
            cleaned = cleaned.slice(1, -1);
        }
        
        // Buscar patrones de texto explicativo comunes y removerlos
        const explicativePatterns = [
            /^(Aquí está|He aquí|Este es|La versión mejorada es|El texto mejorado es|Texto mejorado:|Resultado:|Versión final:)\s*/i,
            /^(Here is|Here's|This is|The improved version is|Improved text:|Result:|Final version:)\s*/i,
        ];
        
        for (const pattern of explicativePatterns) {
            cleaned = cleaned.replace(pattern, '');
        }
        
        // Quitar saltos de línea excesivos al principio y final
        cleaned = cleaned.replace(/^\n+|\n+$/g, '');
        
        console.log('cleanAIResponse input:', text.substring(0, 100) + '...');
        console.log('cleanAIResponse output:', cleaned.substring(0, 100) + '...');
        
        return cleaned;
    }
    
    // Guardar estado actual para poder deshacer cambios de IA
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
        
        console.log('AI History saved. Total entries:', this.aiHistory.length);
    }
    
    // Deshacer el último cambio de IA
    undoAIChange() {
        if (this.aiHistory.length === 0) {
            this.showNotification('No AI changes to undo', 'warning');
            return;
        }
        
        const lastEntry = this.aiHistory.pop();
        
        // Verificar que estamos en la misma nota
        if (lastEntry.noteId !== this.currentNote?.id) {
            this.showNotification('Cannot undo: change from different note', 'warning');
            this.aiHistory.length = 0; // Limpiar historial si cambió de nota
            this.updateUndoButton();
            return;
        }
        
        const editor = document.getElementById('editor');
        editor.innerHTML = lastEntry.content;
        
        this.updateUndoButton();
        this.handleEditorChange();
        this.showNotification('AI change undone');
    }
    
    // Actualizar estado del botón deshacer
    updateUndoButton() {
        const undoBtn = document.getElementById('undo-ai-btn');
        if (undoBtn) {
            undoBtn.disabled = this.aiHistory.length === 0 || 
                              (this.aiHistory.length > 0 && this.aiHistory[this.aiHistory.length -  1].noteId !== this.currentNote?.id);
        }
    }
    
    // Limpiar historial de IA
    clearAIHistory() {
        this.aiHistory.length = 0;
        this.updateUndoButton();
    }
    
    // Función auxiliar para mejoras locales (fallback)
    applyAIImprovement(text, action) {
        const mejoras = {
            claridad: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/\s+/g, ' ')
                    .trim() + ' [Texto mejorado para mayor claridad]';
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
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideDeleteModal() {
        const modal = document.getElementById('delete-modal');
        modal.classList.remove('active');
        this.showMobileFab();
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
    
    // Configuration listeners for advanced controls
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
        
        // Provider change listeners
        const postprocessProvider = document.getElementById('postprocess-provider');
        const transcriptionProvider = document.getElementById('transcription-provider');
        
        if (postprocessProvider) {
            postprocessProvider.addEventListener('change', () => {
                this.updateModelOptions();
            });
        }
        
        if (transcriptionProvider) {
            transcriptionProvider.addEventListener('change', () => {
                this.updateTranscriptionModelOptions();
            });
        }
    }
    
    updateModelOptions() {
        const postprocessProvider = document.getElementById('postprocess-provider').value;
        const postprocessModelSelect = document.getElementById('postprocess-model');
        
        // Limpiar opciones actuales y añadir placeholder
        postprocessModelSelect.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Select model';
        placeholder.disabled = true;
        postprocessModelSelect.appendChild(placeholder);
        
        // Definir modelos por proveedor
        const modelsByProvider = {
            'openai': [
                { value: 'gpt-4o-mini', text: 'GPT-4o Mini (OpenAI)' },
                { value: 'gpt-4o', text: 'GPT-4o (OpenAI)' },
                { value: 'gpt-4.1', text: 'GPT-4.1 (OpenAI)' },
                { value: 'gpt-4.1-mini', text: 'GPT-4.1 Mini (OpenAI)' }
            ],
            'google': [
                { value: 'gemini-2.0-flash', text: 'Gemini 2.0 Flash (Google)' }
            ],
            'openrouter': [
                { value: 'google/gemma-3-27b-it:free', text: 'Gemma 3 27B IT (Free)' },
                { value: 'google/gemini-2.0-flash-exp:free', text: 'Gemini 2.0 Flash Exp (Free)' },
                { value: 'meta-llama/llama-4-maverick:free', text: 'Llama 4 Maverick (Free)' },
                { value: 'meta-llama/llama-4-scout:free', text: 'Llama 4 Scout (Free)' },
                { value: 'deepseek/deepseek-chat-v3-0324:free', text: 'DeepSeek Chat v3 (Free)' },
                { value: 'qwen/qwen3-32b:free', text: 'Qwen 3 32B (Free)' },
                { value: 'mistralai/mistral-small-3.1-24b-instruct:free', text: 'Mistral Small 3.1 24B (Free)' }
            ]
        };
        
        // Añadir opciones según el proveedor seleccionado
        const models = modelsByProvider[postprocessProvider] || [];
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.value;
            option.textContent = model.text;
            postprocessModelSelect.appendChild(option);
        });
        
        // Seleccionar el modelo almacenado si está disponible
        const currentModel = this.config.postprocessModel;
        const availableValues = models.map(m => m.value);
        if (availableValues.includes(currentModel)) {
            postprocessModelSelect.value = currentModel;
        } else {
            postprocessModelSelect.value = '';
        }
    }
    
    async updateTranscriptionModelOptions() {
        const provider = document.getElementById('transcription-provider').value;
        const modelSelect = document.getElementById('transcription-model');
        modelSelect.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Select model';
        placeholder.disabled = true;
        modelSelect.appendChild(placeholder);

        // Get available providers from backend status
        let models = [];
        if (this.availableTranscriptionProviders && this.availableTranscriptionProviders.providers) {
            const found = this.availableTranscriptionProviders.providers.find(p => p.id === provider);
            if (found && found.models) {
                models = found.models;
            }
        }

        // Fallbacks for known providers
        if (provider === 'openai' && models.length === 0) {
            models = ['whisper-1', 'gpt-4o-mini-transcribe', 'gpt-4o-transcribe'];
        }
        if (provider === 'google' && models.length === 0) {
            models = ['google-speech-to-text'];
        }

        // Add options to dropdown
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });

        // Establecer modelo si el almacenado está disponible
        if (models.includes(this.config.transcriptionModel)) {
            modelSelect.value = this.config.transcriptionModel;
        } else {
            modelSelect.value = '';
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
    
    async checkBackendStatus() {
        try {
            const isHealthy = await backendAPI.checkHealth();
            if (!isHealthy) {
                this.showNotification('Backend not available. Check that it is running.', 'error');
                return false;
            }
            
            this.availableAPIs = await backendAPI.checkAPIs();
            
            // Fetch available transcription providers
            try {
                this.availableTranscriptionProviders = await backendAPI.getTranscriptionProviders();
                console.log('Available transcription providers:', this.availableTranscriptionProviders);
            } catch (error) {
                console.error('Error fetching transcription providers:', error);
                this.availableTranscriptionProviders = { providers: [], default: null };
            }
            
            return true;
        } catch (error) {
            console.error('Error checking backend status:', error);
            this.showNotification('Error connecting to backend', 'error');
            return false;
        }
    }

    updateTranscriptionOptions() {
        const selectedModel = document.getElementById('transcription-model').value;
        const streamingOption = document.querySelector('.checkbox-group');
        const promptOption = document.getElementById('transcription-prompt').closest('.model-config');
        
        // Mostrar opciones GPT-4o solo para modelos GPT-4o
        const isGPT4O = selectedModel.includes('gpt-4o');
        
        if (streamingOption) {
            streamingOption.style.display = isGPT4O ? 'block' : 'none';
        }
        
        if (promptOption) {
            promptOption.style.display = isGPT4O ? 'block' : 'none';
        }
        
        // Deshabilitar streaming si no es GPT-4o
        if (!isGPT4O) {
            document.getElementById('streaming-enabled').checked = false;
            document.getElementById('transcription-prompt').value = '';
        }
    }

    updateMobileFabVisibility() {
        const mobileFab = document.getElementById('mobile-record-fab');
        if (!mobileFab) return;

        const shouldShow = this.config.showMobileRecordButton !== false && window.innerWidth <= 768;
        mobileFab.classList.toggle('hidden', !shouldShow);
    }

    hideMobileFab() {
        const mobileFab = document.getElementById('mobile-record-fab');
        if (mobileFab) mobileFab.classList.add('hidden');
    }

    showMobileFab() {
        this.updateMobileFabVisibility();
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
                window.notesApp.showInsertionMarker();
            }
        }, 10);
    }
});

// Manejar atajos de teclado
document.addEventListener('keydown', async (e) => {
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
                    await window.notesApp.createNewNote();
                }
                break;
        }
    }
});

//# sourceMappingURL=app.js.map