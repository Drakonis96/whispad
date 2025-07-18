// Authentication token and current user
let authToken = '';
let currentUser = '';
let isAdmin = false;

const TRANSCRIPTION_PROVIDERS = ['openai', 'local', 'sensevoice'];
const POSTPROCESS_PROVIDERS = ['openai', 'google', 'openrouter', 'groq', 'lmstudio', 'ollama'];
let allowedTranscriptionProviders = [];
let allowedPostprocessProviders = [];
let defaultProviderConfig = {};
let multiUser = true;

const PROVIDER_LABELS = {
    openai: 'OpenAI',
    local: 'Local Whisper',
    sensevoice: 'SenseVoice',
    google: 'Google',
    openrouter: 'OpenRouter',
    groq: 'Groq',
    lmstudio: 'LM Studio',
    ollama: 'Ollama'
};

function safeSetInnerHTML(element, html) {
    element.innerHTML = DOMPurify.sanitize(html);
}

function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (authToken) {
        options.headers['Authorization'] = authToken;
    }
    return fetch(url, options);
}

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
    clarity: {
        nombre: "Improve Clarity",
        descripcion: "Makes text clearer and more direct",
        icono: "✨",
        prompt: "Rewrite the following text in a clearer and more readable way. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the improved text, without additional explanations:",
        visible: true
    },
    formal: {
        nombre: "Make Formal",
        descripcion: "Converts text to a more formal tone",
        icono: "🎩",
        prompt: "Rewrite the following text in a formal tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:",
        visible: false
    },
    casual: {
        nombre: "Make Casual",
        descripcion: "Converts text to a more casual tone",
        icono: "😊",
        prompt: "Rewrite the following text in a casual and friendly tone. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:",
        visible: false
    },
    academic: {
        nombre: "Academic",
        descripcion: "Converts text to academic style",
        icono: "🎓",
        prompt: "Rewrite the following text in an academic style. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the rewritten text, without additional explanations:",
        visible: false
    },
    narrative: {
        nombre: "Narrative",
        descripcion: "Improves narrative texts and novel dialogues",
        icono: "📖",
        prompt: "Improve the following narrative text or novel dialogue, preserving the literary style and narrative voice. Enhance flow, description and literary quality while keeping the essence of the text. Respond ONLY with the improved text, without additional explanations:",
        visible: false
    },
    academic_v2: {
        nombre: "Academic v2",
        descripcion: "Academic improvement with minimal changes, preserving author's words",
        icono: "🎓",
        prompt: "Improve the following academic text by making minimal changes to preserve the author's words. Use more precise wording when necessary, improve the structure and remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Keep the original style and vocabulary as much as possible. Respond ONLY with the improved text, without additional explanations:",
        visible: true
    },
    summarize: {
        nombre: "Summarize",
        descripcion: "Creates a concise summary of the text",
        icono: "📝",
        prompt: "Create a concise summary of the following text. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the summary, without additional explanations:",
        visible: false
    },
    expand: {
        nombre: "Expand",
        descripcion: "Adds more details and context",
        icono: "✚",
        prompt: "Expand the following text by adding more details and relevant context. Remove any interjections or expressions typical of spoken language (mmm, ahhh, eh, um, etc.) and expressions of hesitation when speaking or thinking aloud. Respond ONLY with the expanded text, without additional explanations:",
        visible: true
    },
    translation: {
        nombre: "Translation",
        descripcion: "Translate text into another language",
        icono: "🗣️",
        prompt: "",
        visible: false,
        custom: true
    }
};

// Clase principal de la aplicación
class NotesApp {
    constructor() {
        this.notes = [];
        this.currentNote = null;
        this.isRecording = false;
        this.autoSaveTimeout = null;
        this.autoSaveInterval = null;
        this.saveInProgress = false;
        this.pendingSave = false;
        this.lastSaveHash = '';
        this.searchTerm = '';
        this.selectedText = '';
        this.selectedRange = null;
        this.insertionRange = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audioFileToDelete = null;
        
        // History to undo AI changes
        this.aiHistory = [];
        this.maxHistorySize = 10;
        this.aiInProgress = false;
        this.aiBackupKey = null;

        // Chat conversation history
        this.chatMessages = [];
        this.chatNote = '';

        // Mind map data
        this.mindMapTree = null;
        this.mindMapHistory = [];
        this.mindMapIndex = -1;
        this.graphType = 'mindmap';
        this.graphZoom = 1;
        this.graphPanX = 0;
        this.graphPanY = 0;
        this.graphPanning = false;
        this.graphPanStartX = 0;
        this.graphPanStartY = 0;
        
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
            showMobileRecordButton: true,
            lmstudioHost: '127.0.0.1',
            lmstudioPort: '1234',
            lmstudioModels: '',
            ollamaHost: '127.0.0.1',
            ollamaPort: '11434',
            ollamaModels: '',
            translationEnabled: false,
            translationLanguage: 'en'
        };
        
        // Visible styles configuration
        this.stylesConfig = { ...configuracionMejoras };

        this.overwrittenFiles = new Set();

        this.selectedTags = new Set();

        // Store default language options
        this.defaultLanguageOptions = [];
        
        this.init();
    }
    
    async init() {
        this.loadConfig();
        this.loadStylesConfig();
        this.updateTranslationStyle();
        this.storeDefaultLanguageOptions();
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
        this.setupCollapsibleSections();

        // Migrate existing notes without ID
        await this.migrateExistingNotes();
    }
    
    async migrateExistingNotes() {
        try {
            const response = await authFetch('/api/cleanup-notes', {
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
            if (window.innerWidth <= 900) {
                sidebar.classList.toggle('active');
            } else {
                sidebar.classList.toggle('desktop-hidden');
            }
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
        // Upload audio file
        const uploadBtn = document.getElementById('upload-audio-btn');
        const uploadInput = document.getElementById('upload-audio-input');
        if (uploadBtn && uploadInput) {
            uploadBtn.addEventListener('click', () => {
                this.captureInsertionRange();
                uploadInput.click();
            });
            uploadInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) {
                    await this.uploadAudioFile(file);
                }
                uploadInput.value = '';
            });
        }
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

        const toolsFab = document.getElementById('mobile-tools-fab');
        const toolsMenu = document.getElementById('mobile-tools-menu');
        if (toolsFab && toolsMenu) {
            toolsFab.addEventListener('click', () => {
                toolsMenu.classList.toggle('hidden');
            });
            toolsMenu.querySelectorAll('.mobile-tool-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const target = btn.dataset.target;
                    if (target) {
                        const el = document.getElementById(target);
                        if (el) el.click();
                    }
                    toolsMenu.classList.add('hidden');
                });
            });
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

        const filesBtn = document.getElementById('files-btn');
        if (filesBtn) {
            filesBtn.addEventListener('click', () => {
                this.showAudioModal();
            });
        }

        const closeAudioModal = document.getElementById('close-audio-modal');
        if (closeAudioModal) {
            closeAudioModal.addEventListener('click', () => {
                this.hideAudioModal();
            });
        }

        const playBtn = document.getElementById('play-audio-btn');
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                this.playSelectedAudio();
            });
        }

        const reprocessBtn = document.getElementById('reprocess-audio-btn');
        if (reprocessBtn) {
            reprocessBtn.addEventListener('click', async () => {
                this.captureInsertionRange();
                await this.reprocessSelectedAudio();
            });
        }

        const refreshBtn = document.getElementById('refresh-audio-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                if (this.currentNote) {
                    this.loadAudioDropdown(this.currentNote.id);
                }
            });
        }
        
        // Editor
        const editor = document.getElementById('editor');
        editor.addEventListener('input', () => {
            this.handleEditorChange();
        });

        // Handle paste events to ensure plain text insertion
        editor.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, text);
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

        const cancelDeleteAudio = document.getElementById('cancel-delete-audio');
        if (cancelDeleteAudio) {
            cancelDeleteAudio.addEventListener('click', () => {
                this.hideDeleteAudioModal();
            });
        }

        const confirmDeleteAudio = document.getElementById('confirm-delete-audio');
        if (confirmDeleteAudio) {
            confirmDeleteAudio.addEventListener('click', async () => {
                await this.deleteSelectedAudio();
            });
        }
        
        // Configuración
        document.getElementById('config-btn').addEventListener('click', () => {
            this.showConfigModal();
        });
        
        // Styles configuration
        document.getElementById('styles-config-btn').addEventListener('click', () => {
            this.showStylesConfigModal();
        });

        // Translation settings
        document.getElementById('translation-settings-btn').addEventListener('click', () => {
            this.showTranslationModal();
        });

        document.getElementById('cancel-translation').addEventListener('click', () => {
            this.hideTranslationModal();
        });

        document.getElementById('save-translation').addEventListener('click', () => {
            this.saveTranslationConfig();
        });

        document.getElementById('translation-enabled').addEventListener('change', (e) => {
            const container = document.getElementById('translation-language-container');
            container.style.display = e.target.checked ? 'block' : 'none';
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

        const updateModelsBtn = document.getElementById('update-lmstudio-models-btn');
        if (updateModelsBtn) {
            updateModelsBtn.addEventListener('click', () => {
                this.updateLmStudioModelsList();
            });
        }

        const updateOllamaBtn = document.getElementById('update-ollama-models-btn');
        if (updateOllamaBtn) {
            updateOllamaBtn.addEventListener('click', () => {
                this.updateOllamaModelsList();
            });
        }

        // Custom prompt sidebar
        const promptSidebar = document.getElementById('prompt-sidebar');
        const promptToggle = document.getElementById('prompt-sidebar-toggle');
        const applyPromptBtn = document.getElementById('apply-custom-prompt');
        const customPromptInput = document.getElementById('custom-prompt-text');

        if (promptToggle && promptSidebar) {
            promptToggle.addEventListener('click', () => {
                promptSidebar.classList.toggle('active');
            });
        }

        if (applyPromptBtn && customPromptInput) {
            applyPromptBtn.addEventListener('click', () => {
                const prompt = customPromptInput.value.trim();
                if (!prompt) {
                    this.showNotification('Please enter a prompt', 'warning');
                    return;
                }
                const finalPrompt = `${prompt}\n\nIMPORTANT SYSTEM PROMPT: you must not add any additional comments. Simply follow the previous prompt as instructed and answer in the previous language.`;
                const tempKey = 'temp_custom_prompt';
                this.stylesConfig[tempKey] = {
                    nombre: 'Custom',
                    descripcion: 'Temporary prompt',
                    icono: '💬',
                    prompt: finalPrompt,
                    visible: true,
                    custom: true
                };
                this.improveText(tempKey);
                delete this.stylesConfig[tempKey];
            });
        }

        // Chat sidebar
        const chatSidebar = document.getElementById('chat-sidebar');
        const chatToggle = document.getElementById('chat-sidebar-toggle');
        const chatSend = document.getElementById('chat-send');
        const chatInput = document.getElementById('chat-message-input');
        const chatNew = document.getElementById('chat-new');
        const addFull = document.getElementById('chat-add-full');
        const addSelected = document.getElementById('chat-add-selected');

        if (chatToggle && chatSidebar) {
            chatToggle.addEventListener('click', () => {
                chatSidebar.classList.toggle('active');
            });
        }

        if (addFull && addSelected) {
            addFull.addEventListener('change', () => { if (addFull.checked) addSelected.checked = false; });
            addSelected.addEventListener('change', () => { if (addSelected.checked) addFull.checked = false; });
        }

        if (chatSend && chatInput) {
            chatSend.addEventListener('click', () => { this.sendChatMessage(); });
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }

        if (chatNew) {
            chatNew.addEventListener('click', () => {
                this.chatMessages = [];
                this.chatNote = '';
                this.renderChatMessages();
            });
        }

        const chatResizer = document.getElementById('chat-resizer');
        if (chatResizer && chatSidebar) {
            let startX = 0;
            let startWidth = 0;

            const doDrag = (e) => {
                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const newWidth = Math.max(startWidth + (startX - clientX), 220);
                chatSidebar.style.width = `${newWidth}px`;
                e.preventDefault();
            };

            const stopDrag = () => {
                document.removeEventListener('mousemove', doDrag);
                document.removeEventListener('touchmove', doDrag);
                document.removeEventListener('mouseup', stopDrag);
                document.removeEventListener('touchend', stopDrag);
            };

            const startDrag = (e) => {
                startX = e.touches ? e.touches[0].clientX : e.clientX;
                startWidth = chatSidebar.offsetWidth;
                document.addEventListener('mousemove', doDrag);
                document.addEventListener('touchmove', doDrag);
                document.addEventListener('mouseup', stopDrag);
                document.addEventListener('touchend', stopDrag);
                e.preventDefault();
            };

            chatResizer.addEventListener('mousedown', startDrag);
            chatResizer.addEventListener('touchstart', startDrag);
        }

        // Graph button
        const graphBtn = document.getElementById('graph-btn');
        const graphClose = document.getElementById('close-graph-modal');
        const graphDownload = document.getElementById('download-graph-btn');
        const graphPrev = document.getElementById('prev-graph-btn');
        const graphNext = document.getElementById('next-graph-btn');
        const graphZoomIn = document.getElementById('zoom-in-graph-btn');
        const graphZoomOut = document.getElementById('zoom-out-graph-btn');
        const graphTypeSelect = document.getElementById('graph-type-select');
        const regenerateGraphBtn = document.getElementById('regenerate-graph-btn');
        if (graphBtn) {
            graphBtn.addEventListener('click', () => { this.showGraphModal(); });
        }
        if (graphClose) {
            graphClose.addEventListener('click', () => { this.hideGraphModal(); });
        }
        if (graphDownload) {
            graphDownload.addEventListener('click', () => { this.downloadMindmap(); });
        }
        if (graphPrev) {
            graphPrev.addEventListener('click', () => { this.showPreviousGraph(); });
        }
        if (graphNext) {
            graphNext.addEventListener('click', () => { this.showNextGraph(); });
        }
        if (graphZoomIn) {
            graphZoomIn.addEventListener('click', () => { this.zoomInGraph(); });
        }
        if (graphZoomOut) {
            graphZoomOut.addEventListener('click', () => { this.zoomOutGraph(); });
        }
        if (graphTypeSelect) {
            graphTypeSelect.addEventListener('change', e => {
                this.graphType = e.target.value;
            });
        }
        if (regenerateGraphBtn) {
            regenerateGraphBtn.addEventListener('click', () => {
                this.showGraphModal();
            });
        }

        // Auto-guardado cada 30 segundos
        this.autoSaveInterval = setInterval(() => {
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
        const hasNote = !!this.currentNote;
        if (hasNote) {
            container.classList.remove('hidden');
        } else {
            container.classList.add('hidden');
        }

        const recordBtn = document.getElementById('record-btn');
        const uploadBtn = document.getElementById('upload-audio-btn');
        const mobileFab = document.getElementById('mobile-record-fab');
        if (recordBtn) recordBtn.disabled = !hasNote;
        if (uploadBtn) uploadBtn.disabled = !hasNote;
        if (mobileFab) mobileFab.disabled = !hasNote;
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
            const response = await authFetch('/api/list-saved-notes');
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
            const response = await authFetch(`/api/get-note${params}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            let markdown = data.content || '';

            // Set tags from server response
            note.tags = data.tags || [];

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
        const storageKey = `notes-app-config-${currentUser}`;
        const saved = localStorage.getItem(storageKey);
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
        
        // SenseVoice options
        const detectEmotion = document.getElementById('detect-emotion')?.checked ?? true;
        const detectEvents = document.getElementById('detect-events')?.checked ?? true;
        const useItn = document.getElementById('use-itn')?.checked ?? true;
        
        // Configuración avanzada
        const temperature = parseFloat(document.getElementById('temperature-range').value);
        const maxTokens = parseInt(document.getElementById('max-tokens').value);
        const topP = parseFloat(document.getElementById('top-p-range').value);
        const responseStyle = document.getElementById('response-style').value;
        const showMobileRecordButton = document.getElementById('show-mobile-record').checked;
        const lmstudioHost = document.getElementById('lmstudio-host').value.trim();
        const lmstudioPort = document.getElementById('lmstudio-port').value.trim();
        const lmstudioModels = document.getElementById('lmstudio-models').value.trim();
        const ollamaHost = document.getElementById('ollama-host').value.trim();
        const ollamaPort = document.getElementById('ollama-port').value.trim();
        const ollamaModels = document.getElementById('ollama-models').value.trim();

        this.config = {
            ...this.config, // Mantener otras configuraciones como API keys del .env
            transcriptionProvider,
            postprocessProvider,
            transcriptionModel,
            postprocessModel,
            transcriptionLanguage,
            streamingEnabled,
            transcriptionPrompt,
            detectEmotion,
            detectEvents,
            useItn,
            temperature,
            maxTokens,
            topP,
            responseStyle,
            showMobileRecordButton,
            lmstudioHost,
            lmstudioPort,
            lmstudioModels,
            ollamaHost,
            ollamaPort,
            ollamaModels
        };

        const storageKey = `notes-app-config-${currentUser}`;
        localStorage.setItem(storageKey, JSON.stringify(this.config));

        if (isAdmin) {
            authFetch('/api/update-provider-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lmstudio_host: lmstudioHost,
                    lmstudio_port: lmstudioPort,
                    ollama_host: ollamaHost,
                    ollama_port: ollamaPort
                })
            }).catch(() => {});
        }
        this.updateMobileFabVisibility();
        this.hideConfigModal();
        this.showNotification('Configuration saved');
    }

    showConfigModal() {
        this.loadConfig();
        const tpSelect = document.getElementById('transcription-provider');
        const ppSelect = document.getElementById('postprocess-provider');

        tpSelect.querySelectorAll('option').forEach(opt => {
            if (!opt.value) return;
            if (allowedTranscriptionProviders.length === 0) {
                opt.disabled = true;
                opt.style.display = 'none';
            } else if (!allowedTranscriptionProviders.includes(opt.value)) {
                opt.disabled = true;
                opt.style.display = 'none';
            } else {
                opt.disabled = false;
                opt.style.display = '';
            }
        });

        ppSelect.querySelectorAll('option').forEach(opt => {
            if (!opt.value) return;
            if (allowedPostprocessProviders.length === 0) {
                opt.disabled = true;
                opt.style.display = 'none';
            } else if (!allowedPostprocessProviders.includes(opt.value)) {
                opt.disabled = true;
                opt.style.display = 'none';
            } else {
                opt.disabled = false;
                opt.style.display = '';
            }
        });

        tpSelect.value = this.config.transcriptionProvider;
        ppSelect.value = this.config.postprocessProvider;
        document.getElementById('transcription-model').value = this.config.transcriptionModel || '';
        document.getElementById('postprocess-model').value = this.config.postprocessModel || '';
        document.getElementById('transcription-language').value = this.config.transcriptionLanguage || 'auto';
        
        // Nuevas opciones para GPT-4o
        document.getElementById('streaming-enabled').checked = this.config.streamingEnabled !== false; // true por defecto
        document.getElementById('transcription-prompt').value = this.config.transcriptionPrompt || '';
        
        // SenseVoice options
        if (document.getElementById('detect-emotion')) {
            document.getElementById('detect-emotion').checked = this.config.detectEmotion !== false;
        }
        if (document.getElementById('detect-events')) {
            document.getElementById('detect-events').checked = this.config.detectEvents !== false;
        }
        if (document.getElementById('use-itn')) {
            document.getElementById('use-itn').checked = this.config.useItn !== false;
        }
        
        // Configuración avanzada
        document.getElementById('temperature-range').value = this.config.temperature || 0.3;
        document.getElementById('max-tokens').value = this.config.maxTokens || 1000;
        document.getElementById('top-p-range').value = this.config.topP || 0.95;
        document.getElementById('response-style').value = this.config.responseStyle || 'balanced';
        document.getElementById('show-mobile-record').checked = this.config.showMobileRecordButton !== false;
        document.getElementById('lmstudio-host').value = this.config.lmstudioHost || '127.0.0.1';
        document.getElementById('lmstudio-port').value = this.config.lmstudioPort || '1234';
        document.getElementById('lmstudio-models').value = this.config.lmstudioModels || '';
        document.getElementById('ollama-host').value = this.config.ollamaHost || '127.0.0.1';
        document.getElementById('ollama-port').value = this.config.ollamaPort || '11434';
        document.getElementById('ollama-models').value = this.config.ollamaModels || '';
        
        // Actualizar valores mostrados
        this.updateRangeValues();

        // Filtrar modelos según el proveedor seleccionado
        this.updateModelOptions();
        this.updateTranscriptionModelOptions();
        
        // Mostrar/ocultar opciones GPT-4o según el modelo seleccionado
        this.updateTranscriptionOptions();
        
        // Mostrar/ocultar opciones SenseVoice según el proveedor seleccionado
        this.toggleSenseVoiceOptions();
        // Mostrar/ocultar opciones LM Studio según el proveedor seleccionado
        this.toggleLmStudioOptions();
        // Mostrar/ocultar opciones Ollama según el proveedor seleccionado
        this.toggleOllamaOptions();

        if (!isAdmin) {
            document.querySelectorAll('#config-modal .restricted-option input, #config-modal .restricted-option select, #config-modal .restricted-option textarea, #config-modal .restricted-option button').forEach(el => {
                el.disabled = true;
            });

            if (allowedPostprocessProviders.includes('lmstudio')) {
                document.querySelectorAll('#lmstudio-options input, #lmstudio-options select, #lmstudio-options textarea, #update-lmstudio-models-btn').forEach(el => {
                    el.disabled = false;
                });
            }
            if (allowedPostprocessProviders.includes('ollama')) {
                document.querySelectorAll('#ollama-options input, #ollama-options select, #ollama-options textarea, #update-ollama-models-btn').forEach(el => {
                    el.disabled = false;
                });
            }
        } else {
            document.querySelectorAll('#config-modal .restricted-option input, #config-modal .restricted-option select, #config-modal .restricted-option textarea, #config-modal .restricted-option button').forEach(el => {
                el.disabled = false;
            });
        }

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
        this.loadStylesConfig();
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

    showTranslationModal() {
        const modal = document.getElementById('translation-modal');
        const enabled = document.getElementById('translation-enabled');
        const language = document.getElementById('translation-language');
        enabled.checked = this.config.translationEnabled === true;
        language.value = this.config.translationLanguage || 'en';
        document.getElementById('translation-language-container').style.display = enabled.checked ? 'block' : 'none';
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideTranslationModal() {
        const modal = document.getElementById('translation-modal');
        modal.classList.remove('active');
        this.showMobileFab();
    }

    saveTranslationConfig() {
        const enabled = document.getElementById('translation-enabled').checked;
        const languageSelect = document.getElementById('translation-language');
        const language = languageSelect.value;
        this.config.translationEnabled = enabled;
        this.config.translationLanguage = language;
        const storageKey = `notes-app-config-${currentUser}`;
        localStorage.setItem(storageKey, JSON.stringify(this.config));
        this.updateTranslationStyle();
        this.updateAIButtons();
        this.hideTranslationModal();
        this.showNotification('Translation settings saved');
    }

    renderStylesConfig() {
        const stylesGrid = document.getElementById('styles-grid');
        stylesGrid.innerHTML = '';

        Object.entries(this.stylesConfig).forEach(([key, style]) => {
            const styleItem = document.createElement('div');
            const isCustomStyle = style.custom === true;
            styleItem.className = `style-config-item ${!style.visible ? 'disabled' : ''} ${isCustomStyle ? 'custom-style' : ''}`;
            
            safeSetInnerHTML(styleItem, `
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
            `);

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
        const storageKey = `notes-app-styles-config-${currentUser}`;
        localStorage.setItem(storageKey, JSON.stringify(this.stylesConfig));
        
        // Actualizar botones de IA
        this.updateAIButtons();
        
        // Cerrar modal
        this.hideStylesConfigModal();
        
        this.showNotification('Styles configuration saved');
    }

    loadStylesConfig() {
        const storageKey = `notes-app-styles-config-${currentUser}`;
        const saved = localStorage.getItem(storageKey);
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
        const iconInput = document.getElementById('new-style-icon');
        const descriptionInput = document.getElementById('new-style-description');
        const promptInput = document.getElementById('new-style-prompt');

        const name = nameInput.value.trim();
        const icon = iconInput.value.trim();
        const description = descriptionInput.value.trim();
        const prompt = promptInput.value.trim();

        if (!name || !prompt || !description) {
            this.showNotification('Please complete all fields', 'error');
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
                safeSetInnerHTML(button, `
                    <span class="ai-icon">${style.icono}</span>
                    ${style.nombre}
                `);
                
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
        if (!currentUser) {
            console.warn('Cannot save to storage: currentUser is not set');
            return;
        }
        const storageKey = `notes-app-data-${currentUser}`;
        localStorage.setItem(storageKey, JSON.stringify(this.notes));
    }
    
    async createNewNote() {
        const now = new Date();
        const newNote = {
            id: Date.now(),
            title: `Note ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`,
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

        const backupKey = `ai-backup-${this.currentNote.id}`;
        const backup = localStorage.getItem(backupKey);
        if (backup) {
            this.currentNote.content = backup;
            localStorage.removeItem(backupKey);
            this.showNotification('Restored unsaved content after interrupted AI operation', 'warning');
        }

        document.getElementById('note-title').value = this.currentNote.title;
        safeSetInnerHTML(document.getElementById('editor'), this.currentNote.content);

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
        const audioSelect = document.getElementById('audio-select');
        if (audioSelect) {
            audioSelect.value = '';
        }
        const player = document.getElementById('note-audio-player');
        if (player) {
            player.pause();
            player.removeAttribute('src');
            player.style.display = 'none';
        }
        this.loadAudioDropdown(this.currentNote.id);
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
        if (this.aiInProgress) return;

        const content = document.getElementById('editor').innerHTML;
        if (content === this.currentNote.content) return;

        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            this.saveCurrentNote(true);
        }, 2000);
    }

    handleTitleChange() {
        if (!this.currentNote) return;
        if (this.aiInProgress) return;

        const title = document.getElementById('note-title').value.trim();
        if (title === this.currentNote.title) return;

        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            this.saveCurrentNote(true);
        }, 1000);
    }
    
    saveCurrentNote(silent = false) {
        if (!this.currentNote) return;
        if (this.aiInProgress) return;

        clearTimeout(this.autoSaveTimeout);

        const title = document.getElementById('note-title').value.trim();
        const content = document.getElementById('editor').innerHTML;

        if (silent && title === this.currentNote.title && content === this.currentNote.content) {
            return;
        }
        
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

        const payload = {
            id: this.currentNote.id,
            title: this.currentNote.title,
            content: this.currentNote.content,
            tags: this.currentNote.tags || []
        };

        const hash = JSON.stringify(payload);
        if (this.lastSaveHash === hash && silent) {
            return;
        }
        this.lastSaveHash = hash;

        if (this.saveInProgress) {
            this.pendingSave = true;
            return;
        }

        this.saveInProgress = true;

        try {
            const response = await authFetch('/api/save-note', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
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
        } finally {
            this.saveInProgress = false;
            if (this.pendingSave) {
                this.pendingSave = false;
                this.saveNoteToServer(true);
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
            const response = await authFetch('/api/delete-note', {
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
            const response = await authFetch('/api/download-all-notes');
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

    showAudioModal() {
        if (!this.currentNote) {
            this.showNotification('Please select a note first', 'error');
            return;
        }
        this.loadAudioFiles(this.currentNote.id);
        const modal = document.getElementById('audio-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideAudioModal() {
        const modal = document.getElementById('audio-modal');
        modal.classList.remove('active');
        this.showMobileFab();
    }

    showDeleteAudioModal(fileName) {
        this.audioFileToDelete = fileName;
        const modal = document.getElementById('delete-audio-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideDeleteAudioModal() {
        const modal = document.getElementById('delete-audio-modal');
        modal.classList.remove('active');
        this.showMobileFab();
    }

    async deleteSelectedAudio() {
        if (!this.audioFileToDelete) return;
        try {
            const resp = await authFetch('/api/delete-audio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: this.audioFileToDelete })
            });
            if (resp.ok) {
                await this.loadAudioFiles(this.currentNote.id);
                this.showNotification('File deleted');
            }
        } catch (err) {
            console.error('Error deleting audio', err);
        } finally {
            this.audioFileToDelete = null;
            this.hideDeleteAudioModal();
        }
    }

    showUploadModelsModal() {
        const modal = document.getElementById('upload-model-modal');
        this.hideMobileFab();
        modal.classList.add('active');
        this.loadDownloadedModels();
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

    showGraphModal(topic = null) {
        const noteText = this.getCurrentMarkdown();
        const payload = {
            note: noteText,
            provider: this.config.postprocessProvider || 'openai',
            model: this.config.postprocessModel || 'gpt-3.5-turbo'
        };
        if (topic) payload.topic = topic;
        if (payload.provider === 'lmstudio') {
            payload.host = this.config.lmstudioHost;
            payload.port = this.config.lmstudioPort;
        }
        if (payload.provider === 'ollama') {
            payload.host = this.config.ollamaHost;
            payload.port = this.config.ollamaPort;
        }

        const typeSelect = document.getElementById('graph-type-select');
        if (typeSelect) typeSelect.value = this.graphType;

        const textOutput = document.getElementById('graph-text-output');
        if (textOutput) {
            textOutput.textContent = '';
            textOutput.classList.add('hidden');
        }

        const diagramType = this.graphType || 'mindmap';
        this.showProcessingOverlay(`Generating ${diagramType}...`);

        const modal = document.getElementById('graph-modal');
        const container = document.getElementById('graph-container');

        const handleSvg = (data) => {
            this.mindMapHistory = this.mindMapHistory.slice(0, this.mindMapIndex + 1);
            this.mindMapHistory.push({ tree: data.tree || null, svg: data.svg });
            this.mindMapIndex = this.mindMapHistory.length - 1;
            container.innerHTML = `<div id="graph-pan-zoom">${data.svg}</div>`;
            this.resetGraphTransform();
            this.hideMobileFab();
            modal.classList.add('active');
            this.setupGraphNodeListeners();
            this.updateGraphNavButtons();
        };

        if (diagramType === 'mindmap') {
            backendAPI.generateMindmap(
                payload.note,
                payload.provider,
                payload.model,
                topic,
                payload.host,
                payload.port
            )
            .then(data => {
                if (topic && this.mindMapTree) {
                    this.updateMindMapTree(topic, data.tree);
                } else {
                    this.mindMapTree = data.tree;
                }
                handleSvg(data);
            })
            .catch(err => this.showNotification(err.message || 'Mindmap request failed', 'error'))
            .finally(() => this.hideProcessingOverlay());
        } else {
            backendAPI.generateDiagram(
                payload.note,
                payload.provider,
                payload.model,
                diagramType,
                payload.host,
                payload.port
            )
            .then(data => {
                this.mindMapTree = null;
                handleSvg({ svg: data.svg, tree: data.tree || null });
            })
            .catch(err => this.showNotification(err.message || 'Diagram request failed', 'error'))
            .finally(() => this.hideProcessingOverlay());
        }
    }

    hideGraphModal() {
        const modal = document.getElementById('graph-modal');
        modal.classList.remove('active');
        this.showMobileFab();
        const wrapper = document.getElementById('graph-pan-zoom');
        if (wrapper) {
            wrapper.onmousedown = null;
            wrapper.onwheel = null;
            wrapper.classList.remove('grabbing');
        }
        window.onmousemove = null;
        window.onmouseup = null;
        const output = document.getElementById('graph-text-output');
        if (output) {
            output.textContent = '';
            output.classList.add('hidden');
        }
    }

    downloadMindmap() {
        const svg = document.querySelector('#graph-container svg');
        if (!svg) return;
        const serializer = new XMLSerializer();
        const svgData = serializer.serializeToString(svg);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(svgBlob);
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement('canvas');
            const scale = window.devicePixelRatio || 2;
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            const ctx = canvas.getContext('2d');
            ctx.scale(scale, scale);
            ctx.drawImage(img, 0, 0);
            URL.revokeObjectURL(url);
            canvas.toBlob(blob => {
                const dl = document.createElement('a');
                dl.href = URL.createObjectURL(blob);
                const type = this.graphType || 'mindmap';
                dl.download = `${type}.png`;
                document.body.appendChild(dl);
                dl.click();
                document.body.removeChild(dl);
                URL.revokeObjectURL(dl.href);
            });
        };
        img.src = url;
    }

    showPreviousGraph() {
        if (this.mindMapIndex > 0) {
            this.mindMapIndex -= 1;
            const { tree, svg } = this.mindMapHistory[this.mindMapIndex];
            this.mindMapTree = JSON.parse(JSON.stringify(tree));
            const container = document.getElementById('graph-container');
            container.innerHTML = `<div id="graph-pan-zoom">${svg}</div>`;
            this.resetGraphTransform();
            this.setupGraphNodeListeners();
            this.updateGraphNavButtons();
        }
    }

    showNextGraph() {
        if (this.mindMapIndex < this.mindMapHistory.length - 1) {
            this.mindMapIndex += 1;
            const { tree, svg } = this.mindMapHistory[this.mindMapIndex];
            this.mindMapTree = JSON.parse(JSON.stringify(tree));
            const container = document.getElementById('graph-container');
            container.innerHTML = `<div id="graph-pan-zoom">${svg}</div>`;
            this.resetGraphTransform();
            this.setupGraphNodeListeners();
            this.updateGraphNavButtons();
        }
    }

    updateGraphNavButtons() {
        const prevBtn = document.getElementById('prev-graph-btn');
        const nextBtn = document.getElementById('next-graph-btn');
        if (prevBtn) prevBtn.disabled = this.mindMapIndex <= 0;
        if (nextBtn) nextBtn.disabled = this.mindMapIndex >= this.mindMapHistory.length - 1;
    }

    updateMindMapTree(topic, subtree) {
        const search = (node) => {
            if (!node) return false;
            const title = node.title || node.topic;
            if (title === topic) {
                node.subtopics = subtree.subtopics || [];
                return true;
            }
            if (Array.isArray(node.subtopics)) {
                for (const child of node.subtopics) {
                    if (search(child)) return true;
                }
            }
            return false;
        };
        search(this.mindMapTree);
    }

    setupGraphNodeListeners() {
        const svg = document.querySelector('#graph-container svg');
        if (!svg) return;
        if (this.graphType === 'mindmap') {
            svg.querySelectorAll('text').forEach(t => {
                t.style.cursor = 'pointer';
                t.addEventListener('click', () => {
                    const txt = t.textContent.trim();
                    if (!txt) return;
                    const textMode = document.getElementById('graph-text-toggle')?.checked;
                    if (textMode) {
                        this.exploreGraphTopic(txt);
                    } else {
                        this.showGraphModal(txt);
                    }
                });
            });
        }
        this.setupGraphPanZoom();
    }

    async exploreGraphTopic(topic) {
        const output = document.getElementById('graph-text-output');
        if (!output) return;
        output.textContent = '';
        output.classList.remove('hidden');

        const noteText = this.getCurrentMarkdown();
        const provider = this.config.postprocessProvider;
        const model = this.config.postprocessModel;
        const payload = { note: noteText, messages: [{ role: 'user', content: topic }], stream: true, provider, model };
        if (provider === 'lmstudio') {
            payload.host = this.config.lmstudioHost;
            payload.port = this.config.lmstudioPort;
        }
        if (provider === 'ollama') {
            payload.host = this.config.ollamaHost;
            payload.port = this.config.ollamaPort;
        }

        const response = await authFetch('/api/improve-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok || !response.body) {
            this.showNotification('Chat request failed', 'error');
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (dataStr === '[DONE]') break;
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.content) {
                            output.textContent += data.content;
                            output.scrollTop = output.scrollHeight;
                        }
                        if (data.done) {
                            return;
                        }
                    } catch (e) { continue; }
                }
            }
        }
    }

    resetGraphTransform() {
        this.graphZoom = 1;
        this.graphPanX = 0;
        this.graphPanY = 0;
        this.applyGraphTransform();
    }

    applyGraphTransform() {
        const wrapper = document.getElementById('graph-pan-zoom');
        if (wrapper) {
            wrapper.style.transform = `translate(${this.graphPanX}px, ${this.graphPanY}px) scale(${this.graphZoom})`;
        }
    }

    zoomInGraph() {
        this.graphZoom = Math.min(this.graphZoom * 1.2, 5);
        this.applyGraphTransform();
    }

    zoomOutGraph() {
        this.graphZoom = Math.max(this.graphZoom / 1.2, 0.2);
        this.applyGraphTransform();
    }

    setupGraphPanZoom() {
        const wrapper = document.getElementById('graph-pan-zoom');
        if (!wrapper) return;
        wrapper.style.transformOrigin = '0 0';
        wrapper.classList.remove('grabbing');
        const startPan = (x, y) => {
            this.graphPanning = true;
            this.graphPanStartX = x - this.graphPanX;
            this.graphPanStartY = y - this.graphPanY;
            wrapper.classList.add('grabbing');
        };
        const movePan = (x, y) => {
            if (!this.graphPanning) return;
            this.graphPanX = x - this.graphPanStartX;
            this.graphPanY = y - this.graphPanStartY;
            this.applyGraphTransform();
        };
        const endPan = () => {
            this.graphPanning = false;
            wrapper.classList.remove('grabbing');
        };
        wrapper.onmousedown = e => { e.preventDefault(); startPan(e.clientX, e.clientY); };
        window.onmousemove = e => movePan(e.clientX, e.clientY);
        window.onmouseup = endPan;
        wrapper.onwheel = e => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 1.2 : 0.8;
            this.graphZoom = Math.min(Math.max(this.graphZoom * delta, 0.2), 5);
            this.applyGraphTransform();
        };
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
        
        // Setup advanced model download buttons
        const advancedButtons = document.querySelectorAll('.model-download-advanced');
        advancedButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const model = btn.getAttribute('data-model');
                this.handleAdvancedModelDownload(model);
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
        const response = await authFetch('/api/upload-note', { method: 'POST', body: formData });
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
        safeSetInnerHTML(fileItem, `
            <div class="file-upload-header">
                <span class="file-upload-name">${file.name}</span>
                <span class="file-upload-size">${this.formatFileSize(file.size)}</span>
                <span class="file-upload-status">Preparing...</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar"></div>
            </div>
            <div class="progress-percentage">0%</div>
        `);
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
        safeSetInnerHTML(messageDiv, `
            <i class="fas fa-check-circle message-icon"></i>
            <span class="message-text">All models uploaded successfully! Refreshing providers...</span>
        `);
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
            console.log('Forcing refresh of transcription providers...');
            
            // First, call the backend refresh endpoint to force a fresh check
            try {
                const refreshResult = await backendAPI.refreshProviders();
                console.log('Provider refresh result:', refreshResult);
            } catch (refreshError) {
                console.warn('Error calling refresh endpoint:', refreshError);
            }
            
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
            
            // Update the UI configuration instead of full page reload
            this.updateTranscriptionConfiguration();
            
            // Show notification about new providers
            const sensevoiceAvailable = this.availableTranscriptionProviders?.providers?.some(p => p.id === 'sensevoice');
            if (sensevoiceAvailable) {
                this.showNotification('SenseVoice model loaded successfully! Now available in transcription options.', 'success');
            }
            
        } catch (error) {
            console.error('Error refreshing transcription providers:', error);
        }
    }

    updateTranscriptionConfiguration() {
        try {
            // Update transcription provider options
            this.populateTranscriptionProviders();
            
            // Update model options for current provider
            this.updateTranscriptionModelOptions();
            
            // Update any other UI elements that depend on providers
            this.toggleSenseVoiceOptions();
            
            console.log('Transcription configuration updated successfully');
        } catch (error) {
            console.error('Error updating transcription configuration:', error);
        }
    }

    populateTranscriptionProviders() {
        const transcriptionProviderSelect = document.getElementById('transcription-provider');
        if (!transcriptionProviderSelect) return;

        // Store current selection
        const currentProvider = transcriptionProviderSelect.value;
        
        // Clear existing options
        transcriptionProviderSelect.innerHTML = '';
        
        if (this.availableTranscriptionProviders?.providers) {
            this.availableTranscriptionProviders.providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.id;
                option.textContent = provider.name;
                transcriptionProviderSelect.appendChild(option);
            });
            
            // Restore selection if still available
            if (Array.from(transcriptionProviderSelect.options).some(opt => opt.value === currentProvider)) {
                transcriptionProviderSelect.value = currentProvider;
            } else {
                // Use default provider if current selection is no longer available
                const defaultProvider = this.availableTranscriptionProviders.default;
                if (defaultProvider) {
                    transcriptionProviderSelect.value = defaultProvider;
                }
            }
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
                if (authToken) xhr.setRequestHeader('Authorization', authToken);
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
            const response = await authFetch('/api/upload-model', {
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

    async downloadAdvancedModelWithProgress(model, fileItem) {
        try {
            const streamResponse = await backendAPI.downloadAdvancedModelStream(model);
            await backendAPI.processAdvancedDownloadStream(streamResponse, (percent, status) => {
                const progressBar = fileItem.querySelector('.progress-bar');
                const progressPercentage = fileItem.querySelector('.progress-percentage');
                const statusElement = fileItem.querySelector('.file-upload-status');
                
                if (percent !== undefined) {
                    progressBar.style.width = percent + '%';
                    progressPercentage.textContent = percent + '%';
                }
                if (status) {
                    statusElement.textContent = status;
                    
                    // Special handling for model.pt download progress
                    if (status.includes('model.pt:') && status.includes('MB')) {
                        // Extract progress from status like "Downloading model.pt: 250/936 MB (26.7%)"
                        const match = status.match(/(\d+)\/(\d+) MB/);
                        if (match) {
                            const downloaded = parseInt(match[1]);
                            const total = parseInt(match[2]);
                            statusElement.textContent = `${status} - Large file, please wait...`;
                        }
                    }
                }
            });
            this.updateFileUploadStatus(fileItem, 'success', 'Downloaded successfully');
        } catch (error) {
            console.error('Advanced model download error:', error);
            this.updateFileUploadStatus(fileItem, 'error', `Download failed: ${error.message}`);
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

    async handleAdvancedModelDownload(model) {
        const progressSection = document.getElementById('upload-progress-section');
        const fileUploadList = document.getElementById('file-upload-list');
        progressSection.style.display = 'block';
        fileUploadList.innerHTML = '';

        let filename = '';
        let displayName = '';
        
        switch(model) {
            case 'sensevoice':
                filename = 'SenseVoiceSmall';
                displayName = 'SenseVoice Small';
                break;
            default:
                this.showNotification('Unknown model type', 'error');
                return;
        }

        const fileItem = this.createFileUploadItem({ name: displayName, size: 0 });
        fileUploadList.appendChild(fileItem);

        try {
            await this.downloadAdvancedModelWithProgress(model, fileItem);
            this.showUploadCompleteMessage(fileUploadList);
            await this.forceRefreshTranscriptionProviders();
        } catch (err) {
            this.showNotification(`Error downloading ${displayName}`, 'error');
        }
    }

    async loadDownloadedModels() {
        try {
            const data = await backendAPI.listModels();
            this.renderDownloadedModels(data.models || []);
        } catch (error) {
            console.error('Error loading models:', error);
        }
    }

    renderDownloadedModels(models) {
        const section = document.getElementById('downloaded-models-section');
        const list = document.getElementById('downloaded-models-list');
        if (!section || !list) return;

        list.innerHTML = '';
        if (!models || models.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        models.forEach(m => {
            const li = document.createElement('li');
            li.className = 'model-item';
            safeSetInnerHTML(li, `
                <span class="model-name">${m.name}</span>
                <button class="btn btn--outline btn--sm delete-model-btn" data-name="${m.name}">
                    <i class="fas fa-trash"></i>
                </button>`);
            list.appendChild(li);
        });

        list.querySelectorAll('.delete-model-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const name = btn.getAttribute('data-name');
                if (confirm(`Delete model ${name}?`)) {
                    try {
                        await backendAPI.deleteModel(name);
                        this.loadDownloadedModels();
                        this.showNotification('Model deleted');
                    } catch (err) {
                        console.error('Error deleting model:', err);
                        this.showNotification('Error deleting model', 'error');
                    }
                }
            });
        });
    }

    htmlToMarkdown(html, title) {
        // Crear un elemento temporal para procesar el HTML
        const tempDiv = document.createElement('div');
        safeSetInnerHTML(tempDiv, html);

        let markdown = `# ${title}\n\n`;
        
        // Procesar cada nodo del HTML
        const content = this.processNode(tempDiv);
        
        // Si no hay contenido, añadir un mensaje
        if (!content.trim()) {
            markdown += '*This note is empty*\n';
        } else {
            markdown += content;
        }
        
        return markdown.trim();
    }

    getCurrentMarkdown() {
        const title = document.getElementById('note-title').value.trim() || 'Untitled Note';
        const html = document.getElementById('editor').innerHTML;
        return this.htmlToMarkdown(html, title);
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
        safeSetInnerHTML(container, tags.map(tag => `<span class="tag-badge" data-tag="${tag}">${tag}</span>`).join(''));
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
        safeSetInnerHTML(container, tags.map(t => `<span class="tag-badge" data-tag="${t}">${t}<span class="remove-tag" data-tag="${t}">&times;</span></span>`).join(''));
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
            // Trigger auto-save when tags are modified
            this.scheduleAutoSave();
        }
    }

    removeTag(tag) {
        if (!this.currentNote || !this.currentNote.tags) return;
        this.currentNote.tags = this.currentNote.tags.filter(t => t !== tag);
        this.renderNoteTags(this.currentNote);
        this.renderTagFilter();
        // Trigger auto-save when tags are modified
        this.scheduleAutoSave();
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
        
        safeSetInnerHTML(container, filteredNotes.map(note => {
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
        }).join(''));
        
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
        safeSetInnerHTML(temp, html);
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
        if (!this.currentNote) {
            this.showNotification('Please create or open a note before recording', 'warning');
            return;
        }
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
            
            if (this.config.transcriptionProvider === 'sensevoice' && 
                (!this.availableTranscriptionProviders?.providers || 
                 !this.availableTranscriptionProviders.providers.some(p => p.id === 'sensevoice'))) {
                this.showNotification('SenseVoice not available. Please download the SenseVoiceSmall model first.', 'warning');
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
                await this.saveRecordedAudio(audioBlob);

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
        if (!this.currentNote) {
            this.showNotification('Please create or open a note before transcribing', 'warning');
            return;
        }

        this.showProcessingOverlay('Transcribing audio...');
        
        try {
            let transcription = '';
            
            if (this.config.transcriptionProvider === 'openai') {
                transcription = await this.transcribeWithOpenAI(audioBlob);
            } else if (this.config.transcriptionProvider === 'local') {
                transcription = await this.transcribeWithLocal(audioBlob);
            } else if (this.config.transcriptionProvider === 'sensevoice') {
                transcription = await this.transcribeWithSenseVoice(audioBlob);
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
            throw new Error(`Transcription error: ${error.message}`);
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
            throw new Error(`Error in local transcription: ${error.message}`);
        }
    }

    async transcribeWithSenseVoice(audioBlob) {
        try {
            console.log('🎯 Using SenseVoice transcription');
            console.log('Language:', this.config.transcriptionLanguage);
            
            // Get SenseVoice-specific options
            const detectEmotion = document.getElementById('detect-emotion')?.checked ?? true;
            const detectEvents = document.getElementById('detect-events')?.checked ?? true;
            const useItn = document.getElementById('use-itn')?.checked ?? true;
            
            const result = await backendAPI.transcribeAudioSenseVoice(
                audioBlob,
                this.config.transcriptionLanguage,
                detectEmotion,
                detectEvents,
                useItn
            );
            
            console.log('SenseVoice transcription result:', result);
            
            // Display emotion and events information if available
            if (result.emotion) {
                this.showNotification(`Emotion detected: ${result.emotion.name}`, 'info');
            }
            
            if (result.events && result.events.length > 0) {
                const eventNames = result.events.map(e => e.name).join(', ');
                this.showNotification(`Events detected: ${eventNames}`, 'info');
            }
            
            if (result.language_detected && result.language_detected !== 'auto') {
                this.showNotification(`Language detected: ${result.language_detected}`, 'info');
            }
            
            // Check if we got empty or invalid result
            if (!result.transcription || result.transcription.trim() === '') {
                throw new Error('Empty transcription result from SenseVoice');
            }
            
            return result.transcription;
        } catch (error) {
            console.error('Error in SenseVoice transcription:', error);
            throw new Error(`Error in SenseVoice transcription: ${error.message}`);
        }
    }

    async handleStreamingTranscription(audioBlob, options) {
        try {
            this.showProcessingOverlay('Starting real-time transcription...');
            
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
            statusElement.textContent = 'Transcription error';
            
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

    async uploadAudioFile(file, skipSave = false) {
        if (!this.currentNote) {
            this.showNotification('Please select a note first', 'error');
            return;
        }
        this.showProcessingOverlay(skipSave ? 'Processing audio...' : 'Uploading audio...');
        try {
            const formData = new FormData();
            formData.append('audio', file);
            formData.append('note_id', this.currentNote.id);
            formData.append('language', this.config.transcriptionLanguage);
            formData.append('provider', this.config.transcriptionProvider);
            formData.append('model', this.config.transcriptionModel);
            formData.append('detect_emotion', document.getElementById('detect-emotion')?.checked ?? true);
            formData.append('detect_events', document.getElementById('detect-events')?.checked ?? true);
            formData.append('use_itn', document.getElementById('use-itn')?.checked ?? true);
            formData.append('skip_save', skipSave ? 'true' : 'false');

            const response = await authFetch('/api/upload-audio', { method: 'POST', body: formData });
            const result = await response.json();
            if (response.ok) {
                if (result.transcription) {
                    this.insertTranscription(result.transcription);
                }
                if (!skipSave) {
                    await this.loadAudioFiles(this.currentNote.id);
                }
                this.showNotification(skipSave ? 'Audio processed' : 'Audio uploaded');
            } else {
                this.showNotification(result.error || 'Upload failed', 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Error uploading audio', 'error');
        } finally {
            this.hideProcessingOverlay();
        }
    }

    async saveRecordedAudio(audioBlob) {
        if (!this.currentNote) {
            this.showNotification('Please select a note first', 'error');
            return;
        }
        this.showProcessingOverlay('Saving audio...');
        try {
            const formData = new FormData();

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

            formData.append('audio', audioBlob, filename);
            formData.append('note_id', this.currentNote.id);

            const response = await authFetch('/api/save-audio', { method: 'POST', body: formData });
            const result = await response.json();
            if (response.ok) {
                await this.loadAudioFiles(this.currentNote.id);
                this.showNotification('Audio saved');
            } else {
                this.showNotification(result.error || 'Save failed', 'error');
            }
        } catch (error) {
            console.error('Save audio error:', error);
            this.showNotification('Error saving audio', 'error');
        } finally {
            this.hideProcessingOverlay();
        }
    }

    async loadAudioFiles(noteId) {
        try {
            const response = await authFetch(`/api/list-audios?note_id=${noteId}`);
            if (!response.ok) return;
            const data = await response.json();
            this.renderAudioFiles(data.audios, data.title);
        } catch (err) {
            console.error('Error loading audios', err);
        }
    }

    renderAudioFiles(files, title) {
        const list = document.getElementById('audio-file-list');
        if (!list) return;
        list.innerHTML = '';
        files.forEach(fname => {
            const li = document.createElement('li');
            li.textContent = `${title} - ${fname}`;

            const dl = document.createElement('button');
            dl.className = 'btn btn--outline btn--sm';
            dl.innerHTML = '<i class="fas fa-download"></i>';
            dl.addEventListener('click', () => {
                window.open(`/api/download-audio?filename=${encodeURIComponent(fname)}`);
            });

            const del = document.createElement('button');
            del.className = 'btn btn--error btn--sm';
            del.innerHTML = '<i class="fas fa-trash"></i>';
            del.addEventListener('click', () => {
                this.showDeleteAudioModal(fname);
            });

            const btnWrap = document.createElement('span');
            btnWrap.className = 'file-actions';
            btnWrap.appendChild(dl);
            btnWrap.appendChild(del);
            li.appendChild(btnWrap);
            list.appendChild(li);
        });
    }

    async loadAudioDropdown(noteId) {
        const select = document.getElementById('audio-select');
        if (!select) return;
        select.innerHTML = '';
        if (!noteId) return;
        try {
            const response = await authFetch(`/api/list-audios?note_id=${noteId}`);
            if (!response.ok) return;
            const data = await response.json();
            (data.audios || []).forEach(fname => {
                const opt = document.createElement('option');
                opt.value = fname;
                opt.textContent = fname;
                select.appendChild(opt);
            });
        } catch (err) {
            console.error('Error loading audios', err);
        }
    }

    async playSelectedAudio() {
        const select = document.getElementById('audio-select');
        const player = document.getElementById('note-audio-player');
        if (!select || !player || !select.value) return;

        try {
            const resp = await authFetch(`/api/get-audio?filename=${encodeURIComponent(select.value)}`);
            if (!resp.ok) throw new Error('Failed to fetch audio');
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            player.src = url;
            player.style.display = 'block';
            await player.play();
        } catch (err) {
            console.error('Audio play error', err);
        }
    }

    async reprocessSelectedAudio() {
        const select = document.getElementById('audio-select');
        if (!select || !select.value) return;

        try {
            const resp = await authFetch(`/api/get-audio?filename=${encodeURIComponent(select.value)}`);
            if (!resp.ok) throw new Error('Failed to fetch audio');
            const blob = await resp.blob();
            const file = new File([blob], select.value, { type: blob.type || 'audio/wav' });
            await this.uploadAudioFile(file, true);
        } catch (err) {
            console.error('Audio reprocess error', err);
            this.showNotification('Error reprocessing audio', 'error');
        }
    }
    
    // Mejora con IA
    async improveText(action) {
        if (action === 'translation') {
            this.updateTranslationStyle();
        }
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
        if (!provider || !model) {
            this.showNotification('Please, select a post-processing provider and model', 'error');
            return;
        }
        const isGemini = provider === 'google';
        const isOpenAI = provider === 'openai';
        const isOpenRouter = provider === 'openrouter';
        const isGroq = provider === 'groq';
        const isLmStudio = provider === 'lmstudio';
        const isOllama = provider === 'ollama';

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
        if (isGroq && !this.availableAPIs?.groq) {
            this.showNotification('Groq API not configured in backend', 'warning');
            this.showConfigModal();
            return;
        }

        if (isLmStudio && !this.config.lmstudioHost) {
            this.showNotification('LM Studio host not configured', 'warning');
            this.showConfigModal();
            return;
        }

        if (isOllama && !this.config.ollamaHost) {
            this.showNotification('Ollama host not configured', 'warning');
            this.showConfigModal();
            return;
        }

        // Start AI improvement and create backup
        this.aiInProgress = true;
        this.aiBackupKey = `ai-backup-${this.currentNote?.id}`;
        localStorage.setItem(this.aiBackupKey, document.getElementById('editor').innerHTML);
        clearTimeout(this.autoSaveTimeout);

        // Guardar estado actual para poder deshacer
        this.saveAIHistory();

        this.showProcessingOverlay(`Improving text with AI...`);
        
        let tempSpan;
        let textToImprove = '';
        let rangeToReplace;
        try {
            let improvedText = '';

            // Guardar información importante antes de modificar el DOM
            textToImprove = this.selectedText;
            rangeToReplace = this.selectedRange.cloneRange();
            
            // Crear un elemento span temporal para el streaming con estilo visual
            tempSpan = document.createElement('span');
            tempSpan.className = 'ai-generating-text';
            tempSpan.style.padding = '2px 4px';
            tempSpan.style.borderRadius = '3px';
            tempSpan.style.border = '1px dashed #1976d2';
            tempSpan.textContent = '⏳ Improving...';
            
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
            } else if (isGroq) {
                improvedText = await this.improveWithGroqStream(textToImprove, action, tempSpan);
            } else if (isLmStudio) {
                improvedText = await this.improveWithLmStudioStream(textToImprove, action, tempSpan);
            } else if (isOllama) {
                improvedText = await this.improveWithOllamaStream(textToImprove, action, tempSpan);
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
            const styleName = this.stylesConfig[action]?.nombre || configuracionMejoras[action]?.nombre || action;
            this.showNotification(`Text improved: ${styleName}`);
            this.handleEditorChange();
            localStorage.removeItem(this.aiBackupKey);
            this.aiInProgress = false;
            this.aiBackupKey = null;
            
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
            localStorage.removeItem(this.aiBackupKey);
            this.aiInProgress = false;
            this.aiBackupKey = null;
        }
    }

    async improveWithOpenAI(text, action) {
        try {
            // Verificar si es un estilo personalizado y enviar su prompt
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            
            // Usar el backend en lugar de la API directamente
            return await backendAPI.improveText(text, action, 'openai', false, this.config.postprocessModel, customPrompt);
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
            
            const response = await backendAPI.improveText(text, action, 'openai', true, this.config.postprocessModel, customPrompt);
            
            if (!response.body) {
                throw new Error('No response body received');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let chunkCount = 0;
            const state = { improvedText: '', inThink: false, thinkBuffer: '', tempElement };
            
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
                                this.processThinkChunk(data.content, state);
                                // Mantener la clase de generación durante el streaming
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('Stream marked as done');
                                const finalText = this.cleanAIResponse(state.improvedText);
                                tempElement.textContent = finalText;
                                console.log('Final text set:', finalText);

                                tempElement.className = 'ai-generated-text';
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
                            continue;
                        }
                    }
                }
            }
            
            const finalResult = this.cleanAIResponse(state.improvedText);
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
            return await backendAPI.improveText(text, action, 'google', false, this.config.postprocessModel, customPrompt);
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
            
            const response = await backendAPI.improveText(text, action, 'google', true, this.config.postprocessModel, customPrompt);
            
            if (!response.body) {
                throw new Error('No response body received');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let chunkCount = 0;
            const state = { improvedText: '', inThink: false, thinkBuffer: '', tempElement };
            
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
                                this.processThinkChunk(data.content, state);
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('Gemini stream marked as done');
                                // Asegurar que el texto final esté limpio
                                const finalText = this.cleanAIResponse(state.improvedText);
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
            
            const finalResult = this.cleanAIResponse(state.improvedText);
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

    async improveWithGroq(text, action) {
        try {
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            const model = this.config.postprocessModel;
            return await backendAPI.improveText(text, action, 'groq', false, model, customPrompt);
        } catch (error) {
            throw new Error(`Error improving text with Groq: ${error.message}`);
        }
    }

    async improveWithLmStudio(text, action) {
        try {
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            const model = this.config.postprocessModel;
            const host = this.config.lmstudioHost;
            const port = this.config.lmstudioPort;
            return await backendAPI.improveText(text, action, 'lmstudio', false, model, customPrompt, host, port);
        } catch (error) {
            throw new Error(`Error improving text with LM Studio: ${error.message}`);
        }
    }

    async improveWithOllama(text, action) {
        try {
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            const model = this.config.postprocessModel;
            const host = this.config.ollamaHost;
            const port = this.config.ollamaPort;
            return await backendAPI.improveText(text, action, 'ollama', false, model, customPrompt, host, port);
        } catch (error) {
            throw new Error(`Error improving text with Ollama: ${error.message}`);
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
            
            let chunkCount = 0;
            const state = { improvedText: '', inThink: false, thinkBuffer: '', tempElement };
            
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
                                this.processThinkChunk(data.content, state);
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('OpenRouter stream marked as done');
                                // Asegurar que el texto final esté limpio
                                const finalText = this.cleanAIResponse(state.improvedText);
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
            
            const finalResult = this.cleanAIResponse(state.improvedText);
            console.log('Returning final OpenRouter result:', finalResult);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithOpenRouterStream:', error);
            throw new Error(`Error improving text with OpenRouter: ${error.message}`);
        }
    }

    async improveWithGroqStream(text, action, tempElement) {
        try {
            console.log('Starting Groq stream for action:', action);
            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;
            const model = this.config.postprocessModel;
            const response = await backendAPI.improveText(text, action, 'groq', true, model, customPrompt);

            if (!response.body) {
                throw new Error('No response body received');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let chunkCount = 0;
            const state = { improvedText: '', inThink: false, thinkBuffer: '', tempElement };

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('Groq stream completed. Total chunks:', chunkCount);
                    break;
                }

                chunkCount++;
                const chunk = decoder.decode(value);
                console.log('Received Groq chunk:', chunkCount, chunk);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') {
                                console.log('Received Groq [DONE] signal');
                                break;
                            }

                            const data = JSON.parse(dataStr);
                            console.log('Parsed Groq data:', data);

                            if (data.content) {
                                this.processThinkChunk(data.content, state);
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                console.log('Groq stream marked as done');
                                const finalText = this.cleanAIResponse(state.improvedText);
                                tempElement.textContent = finalText;
                                tempElement.className = 'ai-generated-text';
                                setTimeout(() => { tempElement.className = ''; }, 1000);
                                return finalText;
                            }
                            if (data.error) {
                                console.error('Error in Groq stream data:', data.error);
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse Groq JSON:', parseError, 'Line:', line);
                            continue;
                        }
                    }
                }
            }

            const finalResult = this.cleanAIResponse(state.improvedText);
            console.log('Returning final Groq result:', finalResult);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithGroqStream:', error);
            throw new Error(`Error improving text with Groq: ${error.message}`);
        }
    }

    async improveWithLmStudioStream(text, action, tempElement) {
        try {
            console.log('Starting LM Studio stream for action:', action);

            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;

            const model = this.config.postprocessModel;
            const host = this.config.lmstudioHost;
            const port = this.config.lmstudioPort;
            const response = await backendAPI.improveText(text, action, 'lmstudio', true, model, customPrompt, host, port);

            if (!response.body) {
                throw new Error('No response body received');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            const state = { improvedText: '', inThink: false, thinkBuffer: '', tempElement };
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') {
                                break;
                            }
                            const data = JSON.parse(dataStr);
                            if (data.content) {
                                this.processThinkChunk(data.content, state);
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                const finalText = this.cleanAIResponse(state.improvedText);
                                tempElement.textContent = finalText;
                                tempElement.className = 'ai-generated-text';
                                setTimeout(() => { tempElement.className = ''; }, 1000);
                                return finalText;
                            }
                            if (data.error) {
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            continue;
                        }
                    }
                }
            }

            const finalResult = this.cleanAIResponse(state.improvedText);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithLmStudioStream:', error);
            throw new Error(`Error improving text with LM Studio: ${error.message}`);
        }
    }

    async improveWithOllamaStream(text, action, tempElement) {
        try {
            console.log('Starting Ollama stream for action:', action);

            const style = this.stylesConfig[action];
            const customPrompt = (style && style.custom) ? style.prompt : null;

            const model = this.config.postprocessModel;
            const host = this.config.ollamaHost;
            const port = this.config.ollamaPort;
            const response = await backendAPI.improveText(text, action, 'ollama', true, model, customPrompt, host, port);

            if (!response.body) {
                throw new Error('No response body received');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            const state = { improvedText: '', inThink: false, thinkBuffer: '', tempElement };
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') {
                                break;
                            }
                            const data = JSON.parse(dataStr);
                            if (data.content) {
                                this.processThinkChunk(data.content, state);
                                tempElement.className = 'ai-generating-text';
                            }
                            if (data.done) {
                                const finalText = this.cleanAIResponse(state.improvedText);
                                tempElement.textContent = finalText;
                                tempElement.className = 'ai-generated-text';
                                setTimeout(() => { tempElement.className = ''; }, 1000);
                                return finalText;
                            }
                            if (data.error) {
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            continue;
                        }
                    }
                }
            }

            const finalResult = this.cleanAIResponse(state.improvedText);
            return finalResult;
        } catch (error) {
            console.error('Error in improveWithOllamaStream:', error);
            throw new Error(`Error improving text with Ollama: ${error.message}`);
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

        // Remove <think>...</think> sections if present
        cleaned = cleaned.replace(/<think>.*?<\/think>/gis, '');
        
        // Quitar saltos de línea excesivos al principio y final
        cleaned = cleaned.replace(/^\n+|\n+$/g, '');
        
        console.log('cleanAIResponse input:', text.substring(0, 100) + '...');
        console.log('cleanAIResponse output:', cleaned.substring(0, 100) + '...');

        return cleaned;
    }

    // Handle streaming chunks that may contain <think>...</think> segments
    processThinkChunk(chunk, state) {
        let text = chunk;
        while (text.length > 0) {
            if (state.inThink) {
                const endIdx = text.indexOf('</think>');
                if (endIdx !== -1) {
                    state.thinkBuffer += text.slice(0, endIdx);
                    this.updateProcessingText(state.thinkBuffer.trim());
                    state.thinkBuffer = '';
                    state.inThink = false;
                    text = text.slice(endIdx + 8);
                    this.updateProcessingText('Improving text with AI...');
                } else {
                    state.thinkBuffer += text;
                    this.updateProcessingText(state.thinkBuffer.trim());
                    return;
                }
            } else {
                const startIdx = text.indexOf('<think>');
                if (startIdx !== -1) {
                    state.improvedText += text.slice(0, startIdx);
                    if (state.tempElement) {
                        const cleaned = this.cleanAIResponse(state.improvedText);
                        state.tempElement.textContent = cleaned;
                    }
                    text = text.slice(startIdx + 7);
                    state.inThink = true;
                } else {
                    state.improvedText += text;
                    if (state.tempElement) {
                        const cleaned = this.cleanAIResponse(state.improvedText);
                        state.tempElement.textContent = cleaned;
                    }
                    text = '';
                }
            }
        }
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
        safeSetInnerHTML(editor, lastEntry.content);
        
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
            clarity: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/\s+/g, ' ')
                    .trim() + ' [Texto mejorado para mayor clarity]';
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
            academic: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/muy/g, 'significativamente')
                    .replace(/bueno/g, 'óptimo')
                    .replace(/creo que/g, 'se puede argumentar que')
                    .replace(/porque/g, 'debido a que') + ' [Versión académica]';
            },
            narrative: (texto) => {
                return texto
                    .replace(/\b(y entonces|y luego)\b/g, 'después')
                    .replace(/\b(muy)\b/g, 'sumamente')
                    .replace(/\bdijo\b/g, 'murmuró') + ' [Versión narrativa mejorada]';
            },
            academic_v2: (texto) => {
                return texto
                    .replace(/eh|um|ah|mmm|ahhh/g, '')
                    .replace(/\s+/g, ' ')
                    .trim() + ' [Mejora académica con cambios mínimos]';
            },
            summarize: (texto) => {
                const words = texto.split(' ');
                const summary = words.slice(0, Math.min(20, words.length)).join(' ');
                return `Resumen: ${summary}${words.length > 20 ? '...' : ''}`;
            },
            expand: (texto) => {
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
        textElement.scrollTop = textElement.scrollHeight;
        overlay.classList.add('active');
    }

    updateProcessingText(text) {
        const textElement = document.getElementById('processing-text');
        if (textElement) {
            textElement.textContent = text;
            textElement.scrollTop = textElement.scrollHeight;
        }
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
        safeSetInnerHTML(notification, `
            <div class="notification-content">
                <span class="notification-icon">${type === 'success' ? '✓' : type === 'warning' ? '⚠' : 'ℹ'}</span>
                <span class="notification-message">${message}</span>
            </div>
        `);
        
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
                this.toggleLmStudioOptions();
                this.toggleOllamaOptions();
            });
        }
        
        if (transcriptionProvider) {
            transcriptionProvider.addEventListener('change', () => {
                this.updateTranscriptionModelOptions();
                this.toggleSenseVoiceOptions();
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
                { value: 'mistralai/mistral-small-3.1-24b-instruct:free', text: 'Mistral Small 3.1 24B (Free)' },
                { value: 'moonshotai/kimi-k2:free', text: 'Kimi K2 (Free)' }
            ],
            'groq': [
                { value: 'deepseek-r1-distill-llama-70b', text: 'DeepSeek R1 Distill Llama 70B' },
                { value: 'qwen/qwen3-32b', text: 'Qwen3 32B' },
                { value: 'moonshotai/kimi-k2-instruct', text: 'Kimi K2 Instruct' },
                { value: 'meta-llama/llama-4-scout-17b-16e-instruct', text: 'Llama 4 Scout 17B 16e' },
                { value: 'meta-llama/llama-4-maverick-17b-128e-instruct', text: 'Llama 4 Maverick 17B 128e' }
            ],
            'lmstudio': (this.config.lmstudioModels ? this.config.lmstudioModels.split(',').map(m => ({ value: m.trim(), text: m.trim() })) : []),
            'ollama': (this.config.ollamaModels ? this.config.ollamaModels.split(',').map(m => ({ value: m.trim(), text: m.trim() })) : [])
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

    toggleSenseVoiceOptions() {
        const provider = document.getElementById('transcription-provider').value;
        const sensevoiceOptions = document.getElementById('sensevoice-options');
        
        if (sensevoiceOptions) {
            sensevoiceOptions.style.display = provider === 'sensevoice' ? 'block' : 'none';
        }
        
        // Update language options for SenseVoice
        if (provider === 'sensevoice') {
            this.updateLanguageOptionsForSenseVoice();
        } else {
            this.restoreDefaultLanguageOptions();
        }
    }

    toggleLmStudioOptions() {
        const provider = document.getElementById('postprocess-provider').value;
        const lmstudioOptions = document.getElementById('lmstudio-options');

        if (lmstudioOptions) {
            lmstudioOptions.style.display = provider === 'lmstudio' ? 'block' : 'none';
        }
    }

    toggleOllamaOptions() {
        const provider = document.getElementById('postprocess-provider').value;
        const ollamaOptions = document.getElementById('ollama-options');

        if (ollamaOptions) {
            ollamaOptions.style.display = provider === 'ollama' ? 'block' : 'none';
        }
    }

    updateLmStudioModelsList() {
        const hostInput = document.getElementById('lmstudio-host');
        const portInput = document.getElementById('lmstudio-port');
        const modelsInput = document.getElementById('lmstudio-models');
        if (!hostInput || !portInput || !modelsInput) return;

        const host = hostInput.value.trim();
        const port = portInput.value.trim();

        backendAPI.listLmStudioModels(host, port)
            .then(data => {
                let ids = [];
                if (data.data && Array.isArray(data.data)) {
                    ids = data.data.map(m => m.id || m);
                } else if (Array.isArray(data.models)) {
                    ids = data.models.map(m => m.id || m);
                }
                if (ids.length > 0) {
                    modelsInput.value = ids.join(',');
                    this.config.lmstudioModels = modelsInput.value.trim();
                    this.updateModelOptions();
                    this.showNotification('LM Studio models updated');
                } else {
                    this.showNotification('No models found on LM Studio', 'warning');
                }
            })
            .catch(err => {
                console.error('Error fetching LM Studio models:', err);
                this.showNotification('Failed to fetch LM Studio models', 'error');
            });
    }

    updateOllamaModelsList() {
        const hostInput = document.getElementById('ollama-host');
        const portInput = document.getElementById('ollama-port');
        const modelsInput = document.getElementById('ollama-models');
        if (!hostInput || !portInput || !modelsInput) return;

        const host = hostInput.value.trim();
        const port = portInput.value.trim();

        backendAPI.listOllamaModels(host, port)
            .then(data => {
                let names = [];
                if (Array.isArray(data.models)) {
                    names = data.models.map(m => m.name || m.model || m);
                }
                if (names.length > 0) {
                    modelsInput.value = names.join(',');
                    this.config.ollamaModels = modelsInput.value.trim();
                    this.updateModelOptions();
                    this.showNotification('Ollama models updated');
                } else {
                    this.showNotification('No models found on Ollama', 'warning');
                }
            })
            .catch(err => {
                console.error('Error fetching Ollama models:', err);
                this.showNotification('Failed to fetch Ollama models', 'error');
            });
    }

    updateLanguageOptionsForSenseVoice() {
        const languageSelect = document.getElementById('transcription-language');
        if (!languageSelect) return;
        
        // Store current selection
        const currentValue = languageSelect.value;
        
        // Clear existing options
        languageSelect.innerHTML = '';
        
        // SenseVoice supported languages
        const sensevoiceLanguages = [
            { value: 'auto', text: 'Auto-detect' },
            { value: 'zh', text: 'Chinese (Mandarin)' },
            { value: 'yue', text: 'Chinese (Cantonese)' },
            { value: 'en', text: 'English' },
            { value: 'ja', text: 'Japanese' },
            { value: 'ko', text: 'Korean' },
            { value: 'nospeech', text: 'No Speech' }
        ];
        
        // Add options
        sensevoiceLanguages.forEach(lang => {
            const option = document.createElement('option');
            option.value = lang.value;
            option.textContent = lang.text;
            languageSelect.appendChild(option);
        });
        
        // Restore selection if it's supported, otherwise use auto
        if (sensevoiceLanguages.some(lang => lang.value === currentValue)) {
            languageSelect.value = currentValue;
        } else {
            languageSelect.value = 'auto';
        }
    }

    storeDefaultLanguageOptions() {
        const languageSelect = document.getElementById('transcription-language');
        if (!languageSelect) return;
        this.defaultLanguageOptions = Array.from(languageSelect.options).map(opt => ({
            value: opt.value,
            text: opt.textContent
        }));
    }

    restoreDefaultLanguageOptions() {
        const languageSelect = document.getElementById('transcription-language');
        if (!languageSelect || !this.defaultLanguageOptions.length) return;

        const currentValue = languageSelect.value;
        languageSelect.innerHTML = '';

        this.defaultLanguageOptions.forEach(lang => {
            const option = document.createElement('option');
            option.value = lang.value;
            option.textContent = lang.text;
            languageSelect.appendChild(option);
        });

        if (this.defaultLanguageOptions.some(lang => lang.value === currentValue)) {
            languageSelect.value = currentValue;
        } else {
            languageSelect.value = 'auto';
        }
    }

    updateTranslationStyle() {
        const style = this.stylesConfig.translation;
        if (!style) return;
        if (this.config.translationEnabled) {
            const code = this.config.translationLanguage || 'en';
            let langName = code;
            const select = document.getElementById('translation-language');
            if (select) {
                const opt = select.querySelector(`option[value="${code}"]`);
                if (opt) {
                    langName = opt.textContent;
                }
            }
            style.prompt = `You are a professional translator. Translate the following text into ${langName}, preserving original line breaks, formatting, and punctuation. Respond ONLY with the translated text, without additional explanations.`;
            style.visible = true;
        } else {
            style.visible = false;
        }
    }

    updateMobileFabVisibility() {
        const mobileFab = document.getElementById('mobile-record-fab');
        const toolsFab = document.getElementById('mobile-tools-fab');
        const toolsMenu = document.getElementById('mobile-tools-menu');

        const isMobile = window.innerWidth <= 768;
        if (mobileFab) {
            const shouldShowRecord = this.config.showMobileRecordButton !== false && isMobile;
            mobileFab.classList.toggle('hidden', !shouldShowRecord);
        }
        if (toolsFab) {
            toolsFab.classList.toggle('hidden', !isMobile);
            if (!isMobile && toolsMenu) {
                toolsMenu.classList.add('hidden');
            }
        }
    }

    setupCollapsibleSections() {
        const sections = document.querySelectorAll('.collapsible');
        const handleResize = () => {
            if (window.innerWidth > 768) {
                sections.forEach(sec => sec.classList.remove('collapsed'));
            }
        };
        handleResize();
        window.addEventListener('resize', handleResize);
        sections.forEach(sec => {
            const toggle = sec.querySelector('.collapse-toggle');
            if (toggle) {
                toggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (window.innerWidth <= 768) {
                        sec.classList.toggle('collapsed');
                    }
                });
            }
        });
    }

    hideMobileFab() {
        const mobileFab = document.getElementById('mobile-record-fab');
        const toolsFab = document.getElementById('mobile-tools-fab');
        const toolsMenu = document.getElementById('mobile-tools-menu');
        if (mobileFab) mobileFab.classList.add('hidden');
        if (toolsFab) toolsFab.classList.add('hidden');
        if (toolsMenu) toolsMenu.classList.add('hidden');
    }

    showMobileFab() {
        const toolsMenu = document.getElementById('mobile-tools-menu');
        if (toolsMenu) toolsMenu.classList.add('hidden');
        this.updateMobileFabVisibility();
    }

    renderChatMessages() {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        container.innerHTML = '';
        if (this.chatNote) {
            const noteDiv = document.createElement('div');
            noteDiv.className = 'chat-message system';
            noteDiv.textContent = this.chatNote;
            container.appendChild(noteDiv);
        }
        this.chatMessages.forEach(msg => {
            const div = document.createElement('div');
            div.className = `chat-message ${msg.role}`;
            div.textContent = msg.content;
            container.appendChild(div);
        });
        container.scrollTop = container.scrollHeight;
    }

    async sendChatMessage() {
        const input = document.getElementById('chat-message-input');
        if (!input) return;
        const text = input.value.trim();
        if (!text) return;
        const addFull = document.getElementById('chat-add-full').checked;
        const addSelected = document.getElementById('chat-add-selected').checked;
        let noteText = '';
        if (addFull) {
            noteText = this.getCurrentMarkdown();
        } else if (addSelected) {
            noteText = this.selectedText || '';
        }

        this.chatNote = noteText;

        this.chatMessages.push({ role: 'user', content: text });
        this.renderChatMessages();
        input.value = '';

        const provider = this.config.postprocessProvider;
        const model = this.config.postprocessModel;
        const payload = { note: noteText, messages: this.chatMessages, stream: true, provider, model };
        if (provider === 'lmstudio') {
            payload.host = this.config.lmstudioHost;
            payload.port = this.config.lmstudioPort;
        }
        if (provider === 'ollama') {
            payload.host = this.config.ollamaHost;
            payload.port = this.config.ollamaPort;
        }

        const response = await authFetch('/api/improve-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok || !response.body) {
            this.showNotification('Chat request failed', 'error');
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const assistantMsg = { role: 'assistant', content: '' };
        this.chatMessages.push(assistantMsg);
        const container = document.getElementById('chat-messages');
        const bubble = document.createElement('div');
        bubble.className = 'chat-message assistant';
        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (dataStr === '[DONE]') break;
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.content) {
                            assistantMsg.content += data.content;
                            bubble.textContent += data.content;
                            container.scrollTop = container.scrollHeight;
                        }
                        if (data.done) {
                            bubble.textContent = assistantMsg.content;
                            container.scrollTop = container.scrollHeight;
                            return;
                        }
                    } catch (e) { continue; }
                }
            }
        }
        bubble.textContent = assistantMsg.content;
        container.scrollTop = container.scrollHeight;
    }

    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }
}

// Inicializar la aplicación cuando se carga la página
function initApp() {
    window.notesApp = new NotesApp();
}

document.addEventListener('DOMContentLoaded', async () => {
    const appContent = document.getElementById('app-content');
    const currentUserBtn = document.getElementById('current-user-btn');
    const currentUserText = document.getElementById('current-user-text');
    const logoutBtn = document.getElementById('logout-btn');

    try {
        const resp = await fetch('/api/app-config');
        if (resp.ok) {
            const cfg = await resp.json();
            multiUser = cfg.multi_user;
        }
    } catch (err) {
        console.error('Error fetching app config:', err);
    }

    async function loadDefaultProviderConfig() {
        try {
            const resp = await authFetch('/api/default-provider-config');
            if (resp.ok) {
                defaultProviderConfig = await resp.json();
            }
        } catch (err) {
            console.error('Error fetching default provider config:', err);
        }
    }

    async function restoreSession() {
        const saved = localStorage.getItem('notes-app-session');
        if (!saved) return false;
        try {
            const session = JSON.parse(saved);
            authToken = session.token;
            const resp = await authFetch('/api/session-info');
            if (!resp.ok) {
                localStorage.removeItem('notes-app-session');
                authToken = '';
                return false;
            }
            const data = await resp.json();
            currentUser = data.username;
            allowedTranscriptionProviders = data.transcription_providers || [];
            allowedPostprocessProviders = data.postprocess_providers || [];
            isAdmin = data.is_admin;

            // Clear any old localStorage data from previous sessions
            localStorage.removeItem('notes-app-data'); // Remove old global key

            await loadDefaultProviderConfig();
            if (!isAdmin) {
                const cfgKey = `notes-app-config-${currentUser}`;
                let cfg = {};
                const savedCfg = localStorage.getItem(cfgKey);
                if (savedCfg) cfg = JSON.parse(savedCfg);
                if (defaultProviderConfig.lmstudio_host) {
                    cfg.lmstudioHost = defaultProviderConfig.lmstudio_host;
                    cfg.lmstudioPort = defaultProviderConfig.lmstudio_port;
                }
                if (defaultProviderConfig.ollama_host) {
                    cfg.ollamaHost = defaultProviderConfig.ollama_host;
                    cfg.ollamaPort = defaultProviderConfig.ollama_port;
                }
                localStorage.setItem(cfgKey, JSON.stringify(cfg));
            }
            if (isAdmin) {
                document.querySelectorAll('.admin-only').forEach(el => {
                    if (!el.classList.contains('tab-content')) {
                        el.style.display = '';
                    }
                });
            } else {
                document.querySelectorAll('.admin-only').forEach(el => {
                    if (!el.classList.contains('tab-content')) {
                        el.style.display = 'none';
                    }
                });
            }
            if (currentUserText) currentUserText.textContent = currentUser;
            currentUserBtn.classList.remove('hidden');
            logoutBtn.classList.remove('hidden');
            document.getElementById('user-btn').classList.remove('hidden');
            appContent.classList.remove('hidden');
            initApp();
            return true;
        } catch {
            localStorage.removeItem('notes-app-session');
            authToken = '';
            return false;
        }
    }

    if (multiUser) {
        const restored = await restoreSession();
        if (!restored) {
            window.location.href = 'login.html';
            return;
        }
    } else {
        currentUser = 'admin';
        isAdmin = true;
        try {
            const resp = await fetch('/api/session-info');
            if (resp.ok) {
                const data = await resp.json();
                allowedTranscriptionProviders = data.transcription_providers || [];
                allowedPostprocessProviders = data.postprocess_providers || [];
            }
        } catch (err) {
            console.error('Error fetching session info:', err);
        }
        await loadDefaultProviderConfig();
        currentUserBtn.classList.add('hidden');
        logoutBtn.classList.add('hidden');
        document.getElementById('user-btn').classList.add('hidden');
        appContent.classList.remove('hidden');
        initApp();
    }

    logoutBtn.addEventListener('click', async () => {
        // Stop auto-save immediately to avoid saving with the wrong user
        if (window.notesApp && typeof window.notesApp.destroy === 'function') {
            window.notesApp.destroy();
        }

        await authFetch('/api/logout', { method: 'POST' });
        
        // Clear user-specific localStorage data
        const userStorageKey = `notes-app-data-${currentUser}`;
        localStorage.removeItem(userStorageKey);
        localStorage.removeItem('notes-app-session');
        
        // Also clean up any old global localStorage data that might exist
        localStorage.removeItem('notes-app-data');
        
        authToken = '';
        currentUser = '';
        allowedTranscriptionProviders = [];
        allowedPostprocessProviders = [];
        isAdmin = false;
        currentUserBtn.classList.add('hidden');
        logoutBtn.classList.add('hidden');
        document.getElementById('user-btn').classList.add('hidden');
        document.querySelectorAll('.admin-only').forEach(el => {
            if (!el.classList.contains('tab-content')) {
                el.style.display = 'none';
            }
        });
        // Clear any loaded notes and stop background tasks when logging out
        if (window.notesApp) {
            if (typeof window.notesApp.destroy === 'function') {
                window.notesApp.destroy();
            }
            window.notesApp.notes = [];
            window.notesApp.currentNote = null;
            if (window.notesApp.selectedTags) window.notesApp.selectedTags.clear();
            window.notesApp.searchTerm = '';
            window.notesApp = null;
        }
        const notesList = document.getElementById('notes-list');
        if (notesList) notesList.innerHTML = '';
        const tagFilter = document.getElementById('tag-filter-bar');
        if (tagFilter) tagFilter.innerHTML = '';
        const editor = document.getElementById('editor');
        if (editor) editor.innerHTML = '';
        const noteTitle = document.getElementById('note-title');
        if (noteTitle) noteTitle.value = '';
        document.querySelector('.editor-container')?.classList.add('hidden');
        if (multiUser) {
            window.location.href = 'login.html';
        } else {
            // Force a full page reload to ensure all state is cleared
            window.location.reload(true);
        }
    });

    async function refreshUserList() {
        const listResp = await authFetch('/api/list-users');
        if (listResp.ok) {
            const data = await listResp.json();
            const list = document.getElementById('users-list');
            list.innerHTML = '';
            data.users.filter(u => u.username !== 'admin').forEach(u => {
                const li = document.createElement('li');
                li.className = 'user-item';
                const title = document.createElement('strong');
                title.textContent = u.username;
                li.appendChild(title);

                const tGroup = document.createElement('div');
                tGroup.className = 'provider-group';
                tGroup.append('Transcription: ');
                TRANSCRIPTION_PROVIDERS.forEach(p => {
                    const label = document.createElement('label');
                    label.style.marginRight = '6px';
                    const cb = document.createElement('input');
                    cb.type = 'checkbox';
                    cb.value = p;
                    cb.className = 'edit-transcription';
                    if ((u.transcription_providers || []).includes(p)) cb.checked = true;
                    label.appendChild(cb);
                    label.append(' ' + (PROVIDER_LABELS[p] || p));
                    tGroup.appendChild(label);
                });
                li.appendChild(tGroup);

                const ppGroup = document.createElement('div');
                ppGroup.className = 'provider-group';
                ppGroup.append('Post-process: ');
                POSTPROCESS_PROVIDERS.forEach(p => {
                    const label = document.createElement('label');
                    label.style.marginRight = '6px';
                    const cb = document.createElement('input');
                    cb.type = 'checkbox';
                    cb.value = p;
                    cb.className = 'edit-postprocess';
                    if ((u.postprocess_providers || []).includes(p)) cb.checked = true;
                    label.appendChild(cb);
                    label.append(' ' + (PROVIDER_LABELS[p] || p));
                    ppGroup.appendChild(label);
                });
                li.appendChild(ppGroup);

                const saveBtn = document.createElement('button');
                saveBtn.className = 'btn btn--primary btn--sm';
                saveBtn.textContent = 'Save';
                saveBtn.addEventListener('click', async () => {
                    const tProviders = Array.from(li.querySelectorAll('.edit-transcription:checked')).map(c => c.value);
                    const ppProviders = Array.from(li.querySelectorAll('.edit-postprocess:checked')).map(c => c.value);
                    const resp2 = await authFetch('/api/update-user-providers', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            username: u.username,
                            transcription_providers: tProviders,
                            postprocess_providers: ppProviders
                        })
                    });
                    if (resp2.ok) {
                        alert('Updated ' + u.username);
                    } else {
                        alert('Error updating user');
                    }
                });

                const delBtn = document.createElement('button');
                delBtn.className = 'btn btn--error btn--sm';
                delBtn.textContent = 'Delete';
                delBtn.style.marginLeft = '6px';
                delBtn.addEventListener('click', async () => {
                    if (!confirm('Delete user ' + u.username + '?')) return;
                    const resp3 = await authFetch('/api/delete-user', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username: u.username })
                    });
                    if (resp3.ok) {
                        alert('User deleted');
                        await refreshUserList();
                    } else {
                        alert('Error deleting user');
                    }
                });

                li.appendChild(saveBtn);
                li.appendChild(delBtn);

                list.appendChild(li);
            });
        }
    }

    document.getElementById('user-btn').addEventListener('click', async () => {
        document.getElementById('user-modal').classList.add('active');
        document.querySelectorAll('#user-modal .tab-content').forEach(c => c.style.display = 'none');
        document.getElementById('password-tab').style.display = 'block';
        await refreshUserList();
    });

    document.getElementById('close-user-modal').addEventListener('click', () => {
        document.getElementById('user-modal').classList.remove('active');
    });

    document.querySelectorAll('#user-modal .tab-buttons button').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            document.querySelectorAll('#user-modal .tab-content').forEach(c => c.style.display = 'none');
            document.getElementById(tab).style.display = 'block';
        });
    });

    document.getElementById('change-password-btn').addEventListener('click', async () => {
        const current = document.getElementById('current-password').value;
        const newPass = document.getElementById('new-password').value;
        const confirmPass = document.getElementById('confirm-password').value;
        if (!current || !newPass || !confirmPass) return;
        if (newPass !== confirmPass) {
            alert('Passwords do not match');
            return;
        }
        const resp = await authFetch('/api/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_password: current, new_password: newPass })
        });
        if (resp.ok) {
            alert('Password updated');
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            const data = await resp.json().catch(() => ({}));
            alert(data.error || 'Error updating password');
        }
    });

    const createUserBtn = document.getElementById('create-user-btn');
    createUserBtn.addEventListener('click', async () => {
        const u = document.getElementById('create-username').value.trim();
        const p = document.getElementById('create-password').value;
        if (!u || !p) return;
        createUserBtn.disabled = true;
        const tProviders = Array.from(document.querySelectorAll('.create-transcription-provider:checked')).map(cb => cb.value);
        const ppProviders = Array.from(document.querySelectorAll('.create-postprocess-provider:checked')).map(cb => cb.value);
        const resp = await authFetch('/api/create-user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: u,
                password: p,
                transcription_providers: tProviders,
                postprocess_providers: ppProviders
            })
        });
        createUserBtn.disabled = false;
        if (resp.ok) {
            alert('User created');
            document.getElementById('create-username').value = '';
            document.getElementById('create-password').value = '';
            document.querySelectorAll('#create-tab input[type="checkbox"]').forEach(cb => cb.checked = false);
            await refreshUserList();
        } else {
            const data = await resp.json().catch(() => ({}));
            alert(data.error || 'Error creating user');
        }
    });

    document.getElementById('user-btn').classList.remove('hidden');
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
