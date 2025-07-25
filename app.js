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
    // Merge Authorization header with any provided headers
    const mergedHeaders = { ...(options.headers || {}) };
    if (authToken) {
        mergedHeaders['Authorization'] = authToken;
    }
    return fetch(url, { ...options, headers: mergedHeaders });
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
    remove_emoji: {
        nombre: "Remove emoji",
        descripcion: "Remove all emojis from the text",
        icono: "🫠",
        prompt: "Remove every single emoji from this text. You MUST NOT change nothing from the text, just remove the emojis. Respond ONLY with the improved text, without additional explanations:",
        visible: false
    },
    diarization_fix: {
        nombre: "Fix Speaker Tags",
        descripcion: "Corrects speaker diarization tags",
        icono: "👥",
        prompt: "Correct the speaker diarization in this transcript. Some speaker tags may be incorrectly placed. You MUST NOT modify the text content, only adjust the position of the speaker tags or the text itself. Keep the tags in the format [SPEAKER X]. Respond ONLY with the fixed diarization text, without additional explanations:",
        visible: true
    },
    translation: {
        nombre: "Translation",
        descripcion: "Translate text into another language",
        icono: "🗣️",
        prompt: "",
        visible: false,
        custom: true
    },
    tabularize: {
        nombre: "Tabularize",
        descripcion: "Convert text into a table",
        icono: "\uD83D\uDCCB",
        prompt: "",
        visible: false,
        custom: true
    }
};

// Clase principal de la aplicación
class NotesApp {
    constructor() {
        this.notes = [];
        this.folders = [];
        this.folderStructure = [];
        this.currentNote = null;
        this.noteToDelete = null;
        this.folderToMove = null;
        this.currentViewMode = 'folder'; // 'folder' or 'list'
        this.expandedFolders = new Set();
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
        this.recordingStream = null;
        this.useChunkStreaming = false;
        this.chunkDuration = 0;
        this.chunkTimeout = null;
        
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
            chunkDuration: 30,
            sensevoiceEnableStreaming: false,
            localEnableStreaming: false,
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
            translationLanguage: 'en',
            tabularizeEnabled: false,
            tabularizeLanguage: 'en'
        };
        
        // Visible styles configuration
        this.stylesConfig = { ...configuracionMejoras };

        this.overwrittenFiles = new Set();

        this.selectedTags = new Set();

        // Concept graph settings
        this.conceptNoteScope = 'current'; // current, all, tagged
        this.conceptSelectedTags = new Set();

        // Store default language options
        this.defaultLanguageOptions = [];
        
        this.init();
    }
    
    async init() {
        await this.loadConfig();
        this.loadStylesConfig();
        this.updateTranslationStyle();
        this.updateTabularizeStyle();
        this.storeDefaultLanguageOptions();
        await this.loadNotes();
        this.setupEventListeners();
        this.setupConfigurationListeners();
        this.renderNotesList();
        await this.setupDefaultNote();
        this.updateAIButtons();
        
        // Load view mode preference and initialize folders
        this.loadViewModePreference();
        await this.loadFolderStructure();
        
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
            // Re-check if elements still exist in DOM
            const currentHeaderActions = document.querySelector('.header-actions');
            const currentMobileContainer = document.querySelector('.mobile-header-actions');
            const currentHamburger = document.getElementById('hamburger-menu');
            
            if (!currentHeaderActions || !currentMobileContainer || !currentHamburger) {
                console.warn('Required DOM elements not found during button move operation');
                return;
            }
            
            if (window.innerWidth <= 900) {
                buttons.forEach(btn => {
                    if (btn && btn.parentNode !== currentMobileContainer && document.body.contains(btn)) {
                        currentMobileContainer.appendChild(btn);
                    }
                });
                currentMobileContainer.style.display = 'flex';
            } else {
                buttons.forEach(btn => {
                    if (btn && btn.parentNode !== currentHeaderActions && document.body.contains(btn) && currentHeaderActions.contains(currentHamburger)) {
                        try {
                            currentHeaderActions.insertBefore(btn, currentHamburger);
                        } catch (error) {
                            console.warn('Could not move button back to header:', error);
                            // Fallback: append to header actions if insertBefore fails
                            if (btn.parentNode !== currentHeaderActions) {
                                currentHeaderActions.appendChild(btn);
                            }
                        }
                    }
                });
                currentMobileContainer.style.display = 'none';
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
            if (this.currentViewMode === 'list') {
                this.renderNotesList();
            } else {
                this.renderFolderTree();
            }
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
        this.setupPdfUploadDropZone();
        
        // PDF Upload modal
        document.getElementById('upload-pdf-btn').addEventListener('click', () => {
            this.showUploadPdfModal();
        });

        document.getElementById('cancel-upload-pdf').addEventListener('click', () => {
            this.hideUploadPdfModal();
        });

        document.getElementById('confirm-upload-pdf').addEventListener('click', () => {
            this.processPdfUpload();
        });
        
        // Modal de confirmación
        document.getElementById('cancel-delete').addEventListener('click', () => {
            this.hideDeleteModal();
        });
        
        document.getElementById('confirm-delete').addEventListener('click', async () => {
            if (this.noteToDelete) {
                // Deleting a specific note
                await this.deleteSpecificNote(this.noteToDelete);
                this.noteToDelete = null;
            } else {
                // Deleting the current note
                await this.deleteCurrentNote();
            }
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

        // Tabularize settings
        document.getElementById('tabularize-settings-btn').addEventListener('click', () => {
            this.showTabularizeModal();
        });

        document.getElementById('cancel-tabularize').addEventListener('click', () => {
            this.hideTabularizeModal();
        });

        document.getElementById('save-tabularize').addEventListener('click', () => {
            this.saveTabularizeConfig();
        });

        document.getElementById('tabularize-enabled').addEventListener('change', (e) => {
            const container = document.getElementById('tabularize-language-container');
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
        const conceptGraphBtn = document.getElementById('concept-graph-btn');
        const conceptGraphClose = document.getElementById('close-concept-graph-modal');
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
        if (conceptGraphBtn) {
            conceptGraphBtn.addEventListener('click', () => { this.showConceptGraphModal(); });
        }
        if (conceptGraphClose) {
            conceptGraphClose.addEventListener('click', () => { this.hideConceptGraphModal(); });
        }

        // View mode toggle buttons
        document.getElementById('folder-view-btn').addEventListener('click', () => {
            this.setViewMode('folder');
        });

        document.getElementById('list-view-btn').addEventListener('click', () => {
            this.setViewMode('list');
        });

        // New folder button
        document.getElementById('new-folder-btn').addEventListener('click', () => {
            this.showCreateFolderModal();
        });

        // Create folder modal
        document.getElementById('cancel-create-folder').addEventListener('click', () => {
            this.hideCreateFolderModal();
        });

        document.getElementById('confirm-create-folder').addEventListener('click', async () => {
            await this.createFolder();
        });

        // Move note modal
        document.getElementById('cancel-move-note').addEventListener('click', () => {
            this.hideMoveNoteModal();
        });

        document.getElementById('confirm-move-note').addEventListener('click', async () => {
            await this.moveNoteToFolder();
        });

        // Move folder modal
        const cancelMoveFolder = document.getElementById('cancel-move-folder');
        if (cancelMoveFolder) {
            cancelMoveFolder.addEventListener('click', () => {
                this.hideMoveFolderModal();
            });
        }

        const confirmMoveFolder = document.getElementById('confirm-move-folder');
        if (confirmMoveFolder) {
            confirmMoveFolder.addEventListener('click', async () => {
                await this.moveFolderToFolder();
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
            
            // Refresh the current view
            if (this.currentViewMode === 'folder') {
                await this.loadFolderStructure();
            } else {
                this.renderNotesList();
            }
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
    async loadConfig() {
        const storageKey = `notes-app-config-${currentUser}`;
        const saved = localStorage.getItem(storageKey);
        if (saved) {
            this.config = { ...this.config, ...JSON.parse(saved) };
        }

        try {
            const resp = await authFetch('/api/user-config');
            if (resp.ok) {
                const data = await resp.json();
                if (data && data.config) {
                    this.config = { ...this.config, ...data.config };
                    localStorage.setItem(storageKey, JSON.stringify(this.config));
                }
            }
        } catch (err) {
            console.error('Error loading config from server:', err);
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
        const chunkDuration = parseInt(document.getElementById('chunk-duration').value);

        // SenseVoice options
        const detectEmotion = document.getElementById('detect-emotion')?.checked ?? true;
        const detectEvents = document.getElementById('detect-events')?.checked ?? true;
        const useItn = document.getElementById('use-itn')?.checked ?? true;
        const enableSpeakerDiarization = document.getElementById('enable-speaker-diarization')?.checked ?? false;
        const sensevoiceEnableStreaming = document.getElementById('sensevoice-enable-streaming')?.checked ?? false;

        // Local Whisper options
        const localEnableSpeakerDiarization = document.getElementById('local-enable-speaker-diarization')?.checked ?? false;
        const localEnableStreaming = document.getElementById('local-enable-streaming')?.checked ?? false;
        
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
            chunkDuration,
            detectEmotion,
            detectEvents,
            useItn,
            enableSpeakerDiarization,
            sensevoiceEnableStreaming,
            localEnableSpeakerDiarization,
            localEnableStreaming,
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

        // Guardar configuración en el servidor
        authFetch('/api/user-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.config)
        }).catch(err => {
            console.error('Error saving config on server:', err);
        });

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

    async showConfigModal() {
        await this.loadConfig();
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
        document.getElementById('chunk-duration').value = this.config.chunkDuration || 30;
        
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
        if (document.getElementById('enable-speaker-diarization')) {
            document.getElementById('enable-speaker-diarization').checked = this.config.enableSpeakerDiarization === true;
        }
        if (document.getElementById('sensevoice-enable-streaming')) {
            document.getElementById('sensevoice-enable-streaming').checked = this.config.sensevoiceEnableStreaming === true;
        }

        // Local Whisper options
        if (document.getElementById('local-enable-speaker-diarization')) {
            document.getElementById('local-enable-speaker-diarization').checked = this.config.localEnableSpeakerDiarization === true;
        }
        if (document.getElementById('local-enable-streaming')) {
            document.getElementById('local-enable-streaming').checked = this.config.localEnableStreaming === true;
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

        // Guardar configuración en el servidor
        authFetch('/api/user-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.config)
        }).catch(err => {
            console.error('Error saving config on server:', err);
        });
        this.updateTranslationStyle();
        this.updateAIButtons();
        this.hideTranslationModal();
        this.showNotification('Translation settings saved');
    }

    showTabularizeModal() {
        const modal = document.getElementById('tabularize-modal');
        const enabled = document.getElementById('tabularize-enabled');
        const language = document.getElementById('tabularize-language');
        enabled.checked = this.config.tabularizeEnabled === true;
        language.value = this.config.tabularizeLanguage || 'en';
        document.getElementById('tabularize-language-container').style.display = enabled.checked ? 'block' : 'none';
        this.hideMobileFab();
        modal.classList.add('active');
    }

    hideTabularizeModal() {
        const modal = document.getElementById('tabularize-modal');
        modal.classList.remove('active');
        this.showMobileFab();
    }

    saveTabularizeConfig() {
        const enabled = document.getElementById('tabularize-enabled').checked;
        const languageSelect = document.getElementById('tabularize-language');
        const language = languageSelect.value;
        this.config.tabularizeEnabled = enabled;
        this.config.tabularizeLanguage = language;
        const storageKey = `notes-app-config-${currentUser}`;
        localStorage.setItem(storageKey, JSON.stringify(this.config));

        authFetch('/api/user-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.config)
        }).catch(err => {
            console.error('Error saving config on server:', err);
        });
        this.updateTabularizeStyle();
        this.updateAIButtons();
        this.hideTabularizeModal();
        this.showNotification('Tabularize settings saved');
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

        // Guardar configuración en el servidor
        authFetch('/api/user-styles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.stylesConfig)
        }).catch(err => {
            console.error('Error saving styles on server:', err);
        });
        
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

        // Cargar estilos desde el servidor
        authFetch('/api/user-styles')
            .then(resp => resp.ok ? resp.json() : null)
            .then(data => {
                if (data && data.styles) {
                    Object.keys(data.styles).forEach(key => {
                        this.stylesConfig[key] = data.styles[key];
                    });
                }
            })
            .catch(err => {
                console.error('Error loading styles from server:', err);
            });
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

    // === FOLDER MANAGEMENT FUNCTIONS ===
    
    loadViewModePreference() {
        const storageKey = `notes-app-view-mode-${currentUser}`;
        const savedMode = localStorage.getItem(storageKey);
        const mode = savedMode || 'folder'; // Default to folder view
        
        this.setViewMode(mode);
    }
    
    async loadFolderStructure() {
        try {
            const response = await authFetch('/api/folder-structure');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.folderStructure = data.structure || [];
            
            if (this.currentViewMode === 'folder') {
                this.renderFolderTree();
                // Update tag filter to include tags from folder structure
                this.renderTagFilter();
            }
        } catch (error) {
            console.error('Error loading folder structure:', error);
            this.folderStructure = [];
        }
    }
    
    setViewMode(mode) {
        this.currentViewMode = mode;
        
        // Update button states
        document.querySelectorAll('.view-mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        
        // Toggle visibility of views
        const notesList = document.getElementById('notes-list');
        const folderTree = document.getElementById('folder-tree');
        
        if (mode === 'folder') {
            notesList.style.display = 'none';
            folderTree.style.display = 'block';
            this.loadFolderStructure();
        } else {
            notesList.style.display = 'block';
            folderTree.style.display = 'none';
            this.renderNotesList();
        }
        
        // Save preference
        const storageKey = `notes-app-view-mode-${currentUser}`;
        localStorage.setItem(storageKey, mode);
    }
    
    renderFolderTree() {
        const container = document.getElementById('folder-tree');
        if (!container) return;
        
        // Only render folder view if we're in folder mode
        if (this.currentViewMode !== 'folder') {
            return;
        }
        
        if (!this.folderStructure.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📁</div>
                    <h3>No notes yet</h3>
                    <p>Create your first note to get started</p>
                </div>
            `;
            return;
        }
        
        // Apply search and tag filtering
        let filteredStructure = this.folderStructure;
        if (this.searchTerm || this.selectedTags.size > 0) {
            filteredStructure = this.filterFolderStructure(this.folderStructure);
        }
        
        container.innerHTML = this.renderFolderItems(filteredStructure);
        this.attachFolderEventListeners();
    }
    
    // Refresh the current view based on view mode
    refreshCurrentView() {
        if (this.currentViewMode === 'folder') {
            this.renderFolderTree();
        } else {
            this.renderNotesList();
        }
    }

    filterFolderStructure(items) {
        return items.map(item => {
            if (item.type === 'folder') {
                // Recursively filter children
                const filteredChildren = this.filterFolderStructure(item.children || []);
                
                // Include folder if it has matching children or if folder name matches search
                if (filteredChildren.length > 0 || 
                    (this.searchTerm && item.name.toLowerCase().includes(this.searchTerm))) {
                    return {
                        ...item,
                        children: filteredChildren
                    };
                }
                return null;
            } else {
                // It's a note - check if it matches search and tag filters
                let matchesSearch = true;
                let matchesTags = true;
                
                // Apply search filter
                if (this.searchTerm) {
                    matchesSearch = item.name.toLowerCase().includes(this.searchTerm) || 
                                   (item.content && item.content.toLowerCase().includes(this.searchTerm));
                }
                
                // Apply tag filter
                if (this.selectedTags.size > 0) {
                    const noteTags = item.tags || [];
                    matchesTags = [...this.selectedTags].every(selectedTag => 
                        noteTags.some(noteTag => noteTag.toLowerCase() === selectedTag.toLowerCase())
                    );
                }
                
                if (matchesSearch && matchesTags) {
                    return item;
                }
                return null;
            }
        }).filter(item => item !== null);
    }
    
    renderFolderItems(items, level = 0) {
        return items.map(item => {
            if (item.type === 'folder') {
                const isExpanded = this.expandedFolders.has(item.path);
                const hasChildren = item.children && item.children.length > 0;
                
                return `
                    <div class="folder-item" data-path="${item.path}" data-level="${level}">
                        <div class="folder-toggle ${isExpanded ? 'expanded' : ''}" ${hasChildren ? '' : 'style="visibility: hidden;"'}>
                            <i class="fas fa-chevron-right"></i>
                        </div>
                        <div class="folder-icon">
                            <i class="fas fa-folder${isExpanded ? '-open' : ''}"></i>
                        </div>
                        <div class="folder-name">${item.name}</div>
                        <div class="folder-actions">
                            <button class="folder-action-btn" data-action="create-note" title="Create note in this folder">
                                <i class="fas fa-plus"></i>
                            </button>
                            <button class="folder-action-btn" data-action="move" title="Move folder">
                                <i class="fas fa-folder-open"></i>
                            </button>
                            <button class="folder-action-btn" data-action="delete" title="Delete folder">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    ${isExpanded && hasChildren ? `
                        <div class="folder-children">
                            ${this.renderFolderItems(item.children, level + 1)}
                        </div>
                    ` : ''}
                `;
            } else {
                // It's a note
                const isActive = this.currentNote && this.currentNote.id === item.id;
                return `
                    <div class="folder-note-item ${isActive ? 'active' : ''}" data-id="${item.id}" data-level="${level}">
                        <div class="folder-note-icon">
                            <i class="fas fa-file-alt"></i>
                        </div>
                        <div class="folder-note-title">${item.name}</div>
                        <div class="folder-note-actions">
                            <button class="folder-note-action-btn" data-action="move" title="Move note">
                                <i class="fas fa-folder-open"></i>
                            </button>
                            <button class="folder-note-action-btn note-delete-btn" data-note-id="${item.id}" data-action="delete" title="Delete note">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            }
        }).join('');
    }
    
    attachFolderEventListeners() {
        const container = document.getElementById('folder-tree');
        if (!container) return;
        
        // Folder toggle events
        container.querySelectorAll('.folder-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const folderItem = toggle.closest('.folder-item');
                const path = folderItem.dataset.path;
                this.toggleFolder(path);
            });
        });
        
        // Folder click events
        container.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                this.toggleFolder(path);
            });
        });
        
        // Note click events
        container.querySelectorAll('.folder-note-item').forEach(item => {
            item.addEventListener('click', async () => {
                const noteId = parseInt(item.dataset.id);
                await this.selectNoteFromFolder(noteId);
            });
        });
        
        // Folder action events
        container.querySelectorAll('.folder-action-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const folderItem = btn.closest('.folder-item');
                const path = folderItem.dataset.path;
                
                if (action === 'delete') {
                    await this.deleteFolder(path);
                } else if (action === 'create-note') {
                    await this.createNoteInFolder(path);
                } else if (action === 'move') {
                    this.showMoveFolderModal(path);
                }
            });
        });
        
        // Note action events
        container.querySelectorAll('.folder-note-action-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const noteItem = btn.closest('.folder-note-item');
                const noteId = parseInt(noteItem.dataset.id);
                
                if (action === 'move') {
                    this.showMoveNoteModal(noteId);
                } else if (action === 'delete') {
                    this.showDeleteNoteModal(noteId);
                }
            });
        });
    }
    
    toggleFolder(path) {
        if (this.expandedFolders.has(path)) {
            this.expandedFolders.delete(path);
        } else {
            this.expandedFolders.add(path);
        }
        this.renderFolderTree();
    }
    
    async selectNoteFromFolder(noteId) {
        // Find the note in folder structure
        const note = this.findNoteInStructure(noteId, this.folderStructure);
        if (!note) return;
        
        // Add to notes array if not already there (for compatibility)
        if (!this.notes.find(n => n.id === noteId)) {
            this.notes.push({
                id: note.id,
                filename: note.filename,
                title: note.name,
                content: '',
                createdAt: note.created,
                updatedAt: note.modified,
                tags: note.tags || [],
                loaded: false
            });
        }
        
        await this.selectNote(noteId);
    }
    
    findNoteInStructure(noteId, items) {
        for (const item of items) {
            if (item.type === 'note' && item.id === noteId) {
                return item;
            } else if (item.type === 'folder' && item.children) {
                const found = this.findNoteInStructure(noteId, item.children);
                if (found) return found;
            }
        }
        return null;
    }
    
    showCreateFolderModal() {
        const modal = document.getElementById('create-folder-modal');
        const nameInput = document.getElementById('folder-name-input');
        const parentSelect = document.getElementById('parent-folder-select');
        
        // Clear previous values
        nameInput.value = '';
        
        // Populate parent folder options
        this.populateFolderOptions(parentSelect);
        
        modal.classList.add('active');
        nameInput.focus();
    }
    
    hideCreateFolderModal() {
        const modal = document.getElementById('create-folder-modal');
        modal.classList.remove('active');
    }
    
    populateFolderOptions(select, excludePath = null) {
        select.innerHTML = '<option value="">Root (No parent)</option>';
        this.addFolderOptions(select, this.folderStructure, '', excludePath);
    }

    addFolderOptions(select, items, prefix = '', excludePath = null) {
        items.forEach(item => {
            if (item.type === 'folder') {
                const shouldExclude = excludePath && item.path.startsWith(excludePath);
                if (!shouldExclude) {
                    const option = document.createElement('option');
                    option.value = item.path;
                    option.textContent = prefix + item.name;
                    select.appendChild(option);
                }

                if (item.children) {
                    this.addFolderOptions(select, item.children, prefix + item.name + '/', excludePath);
                }
            }
        });
    }
    
    async createFolder() {
        const nameInput = document.getElementById('folder-name-input');
        const parentSelect = document.getElementById('parent-folder-select');
        
        const name = nameInput.value.trim();
        const parent = parentSelect.value;
        
        if (!name) {
            this.showNotification('Please enter a folder name', 'error');
            return;
        }
        
        try {
            const response = await authFetch('/api/folders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    parent: parent
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create folder');
            }
            
            this.showNotification('Folder created successfully');
            this.hideCreateFolderModal();
            await this.loadFolderStructure();
            
        } catch (error) {
            console.error('Error creating folder:', error);
            this.showNotification(`Error creating folder: ${error.message}`, 'error');
        }
    }
    
    findFolderInStructure(targetPath, items) {
        for (const item of items) {
            if (item.type === 'folder') {
                if (item.path === targetPath) {
                    return item;
                }
                if (item.children) {
                    const found = this.findFolderInStructure(targetPath, item.children);
                    if (found) return found;
                }
            }
        }
        return null;
    }

    async deleteFolder(path) {
        const folder = this.findFolderInStructure(path, this.folderStructure);
        let confirmMessage = 'Are you sure you want to delete this folder?';
        let force = false;
        if (folder && folder.children && folder.children.length > 0) {
            confirmMessage = 'This action will delete the selected folder and all its contents. Do you want to continue?';
            force = true;
        }

        if (!confirm(confirmMessage)) {
            return;
        }

        try {
            const url = `/api/folders/${encodeURIComponent(path)}${force ? '?force=true' : ''}`;
            const response = await authFetch(url, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete folder');
            }
            
            this.showNotification('Folder deleted successfully');
            await this.loadFolderStructure();
            
        } catch (error) {
            console.error('Error deleting folder:', error);
            this.showNotification(`Error deleting folder: ${error.message}`, 'error');
        }
    }
    
    async createNoteInFolder(folderPath) {
        const now = new Date();
        const newNote = {
            id: Date.now(),
            title: `Note ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`,
            content: '',
            createdAt: now.toISOString(),
            updatedAt: now.toISOString(),
            loaded: true
        };
        
        this.notes.unshift(newNote);
        this.saveToStorage();
        
        // Select the note first so currentNote is set
        this.currentNote = newNote;
        
        try {
            // Create the note directly in the target folder
            const response = await authFetch('/api/create-note-in-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: newNote.id,
                    title: newNote.title,
                    content: newNote.content,
                    folder_path: folderPath,
                    tags: newNote.tags || []
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create note in folder');
            }
            
            // Expand the folder to show the new note
            if (!this.expandedFolders.has(folderPath)) {
                this.expandedFolders.add(folderPath);
            }
            
            // Refresh folder structure to show the new note
            await this.loadFolderStructure();
            this.renderFolderTree();
            
            // Update selection UI
            this.updateNoteSelection();
            this.loadNoteToEditor();
            
            // Focus the title for editing
            setTimeout(() => {
                document.getElementById('note-title').focus();
                document.getElementById('note-title').select();
            }, 100);
            
            this.showNotification('Note created in folder successfully');
            
        } catch (error) {
            console.error('Error creating note in folder:', error);
            this.showNotification(`Error creating note in folder: ${error.message}`, 'error');
        }
    }
    
    showMoveNoteModal(noteId) {
        this.noteToMove = noteId;
        const modal = document.getElementById('move-note-modal');
        const targetSelect = document.getElementById('target-folder-select');
        
        // Populate folder options
        this.populateFolderOptions(targetSelect);
        
        modal.classList.add('active');
    }
    
    hideMoveNoteModal() {
        const modal = document.getElementById('move-note-modal');
        modal.classList.remove('active');
        this.noteToMove = null;
    }
    
    async moveNoteToFolder() {
        if (!this.noteToMove) return;
        
        const targetSelect = document.getElementById('target-folder-select');
        const targetFolder = targetSelect.value;
        
        try {
            const response = await authFetch('/api/move-note', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    note_id: this.noteToMove,
                    folder: targetFolder
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to move note');
            }
            
            this.showNotification('Note moved successfully');
            this.hideMoveNoteModal();
            await this.loadFolderStructure();
            
        } catch (error) {
            console.error('Error moving note:', error);
            this.showNotification(`Error moving note: ${error.message}`, 'error');
        }
    }

    showMoveFolderModal(folderPath) {
        this.folderToMove = folderPath;
        const modal = document.getElementById('move-folder-modal');
        const targetSelect = document.getElementById('target-parent-folder-select');

        // Populate folder options excluding the folder being moved
        targetSelect.innerHTML = '<option value="">Root (No parent)</option>';
        this.addFolderOptions(targetSelect, this.folderStructure, '', folderPath);

        modal.classList.add('active');
    }

    hideMoveFolderModal() {
        const modal = document.getElementById('move-folder-modal');
        modal.classList.remove('active');
        this.folderToMove = null;
    }

    async moveFolderToFolder() {
        if (!this.folderToMove) return;

        const targetSelect = document.getElementById('target-parent-folder-select');
        const targetFolder = targetSelect.value;

        try {
            const response = await authFetch('/api/move-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_path: this.folderToMove,
                    target_folder: targetFolder
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to move folder');
            }

            this.showNotification('Folder moved successfully');
            this.hideMoveFolderModal();
            await this.loadFolderStructure();

        } catch (error) {
            console.error('Error moving folder:', error);
            this.showNotification(`Error moving folder: ${error.message}`, 'error');
        }
    }
    
    // === END FOLDER MANAGEMENT FUNCTIONS ===
    
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
        
        // Select the note first so currentNote is set
        this.currentNote = newNote;
        
        // If in folder view, add the note to the root of the folder structure immediately
        if (this.currentViewMode === 'folder') {
            // Add the new note to the root of the folder structure for immediate display
            const folderNote = {
                id: newNote.id,
                type: 'note',
                name: newNote.title,
                filename: `${newNote.id}.md`,
                created: newNote.createdAt,
                modified: newNote.updatedAt,
                tags: []
            };
            this.folderStructure.unshift(folderNote);
            this.renderFolderTree();
        } else {
            this.renderNotesList();
        }
        
        // Update selection UI immediately
        this.updateNoteSelection();
        this.loadNoteToEditor();
        
        // Save the new note to the server in the background
        this.saveNoteToServer(true).then(() => {
            // After saving to server, reload folder structure to get the correct server state
            if (this.currentViewMode === 'folder') {
                this.loadFolderStructure().then(() => {
                    this.renderFolderTree();
                    this.updateNoteSelection();
                });
            }
        });
        
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
        // Clear active state from both list view and folder view notes
        document.querySelectorAll('.note-item, .folder-note-item').forEach(item => {
            item.classList.remove('active');
        });
        
        if (this.currentNote) {
            // Try both selectors for list view and folder view
            const activeItem = document.querySelector(`[data-note-id="${this.currentNote.id}"], [data-id="${this.currentNote.id}"]`);
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

        // Immediate local update for folder view
        if (this.currentView === 'folders' && title) {
            const oldTitle = this.currentNote.title;
            this.currentNote.title = title; // Temporarily update for UI
            this.updateNoteInFolderStructure(this.currentNote.id, title);
            this.currentNote.title = oldTitle; // Restore original title until save
        }

        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            this.saveCurrentNote(true);
        }, 1000);
    }

    scheduleAutoSave() {
        if (!this.currentNote) return;
        if (this.aiInProgress) return;

        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            this.saveCurrentNote(true);
        }, 500); // Shorter timeout for tag changes
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
        
        const titleChanged = this.currentNote.title !== (title || 'Untitled Note');
        
        this.currentNote.title = title || 'Untitled Note';
        this.currentNote.content = content;
        this.currentNote.updatedAt = new Date().toISOString();

        // Save to local storage
        this.saveToStorage();
        
        // Refresh current view
        if (this.currentViewMode === 'folder') {
            // If title changed, update local folder structure immediately for instant feedback
            if (titleChanged) {
                this.updateNoteInFolderStructure(this.currentNote.id, this.currentNote.title);
                this.renderFolderTree();
                this.updateNoteSelection();
                
                // Then save to server and refresh from server to get the authoritative state
                this.saveNoteToServer(true).then(() => {
                    this.loadFolderStructure().then(() => {
                        this.renderFolderTree();
                        this.updateNoteSelection();
                    });
                });
            } else {
                this.renderFolderTree();
            }
        } else {
            this.renderNotesList();
        }
        
        this.updateNoteSelection();

        this.currentNote.loaded = true;
        
        // Save to server as markdown file
        if (!titleChanged) {
            // Only save if title didn't change (to avoid double save)
            this.saveNoteToServer(silent);
        }
        
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
        
        // Refresh current view
        if (this.currentViewMode === 'folder') {
            // Remove the note from current folder structure for immediate UI update
            this.removeNoteFromFolderStructure(noteIdToDelete);
            this.renderFolderTree();
        } else {
            this.renderNotesList();
        }
        
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

    showUploadPdfModal() {
        if (!this.currentNote) {
            this.showNotification('Please select a note first', 'error');
            return;
        }
        const modal = document.getElementById('upload-pdf-modal');
        this.hideMobileFab();
        modal.classList.add('active');
        // Reset modal state
        this.selectedPdfFile = null;
        document.getElementById('confirm-upload-pdf').disabled = true;
        const progressSection = document.getElementById('pdf-upload-progress-section');
        const uploadList = document.getElementById('pdf-upload-list');
        progressSection.style.display = 'none';
        uploadList.innerHTML = '';
    }

    hideUploadPdfModal() {
        const modal = document.getElementById('upload-pdf-modal');
        modal.classList.remove('active');
        this.showMobileFab();
        this.selectedPdfFile = null;
    }

    async processPdfUpload() {
        if (!this.selectedPdfFile || !this.currentNote) {
            return;
        }

        const progressSection = document.getElementById('pdf-upload-progress-section');
        const uploadList = document.getElementById('pdf-upload-list');
        progressSection.style.display = 'block';
        uploadList.innerHTML = '';

        // Create file upload item for progress display
        const fileItem = this.createFileUploadItem(this.selectedPdfFile);
        uploadList.appendChild(fileItem);

        try {
            // Upload and process the file
            const result = await this.uploadPdfFileWithProgress(this.selectedPdfFile, fileItem);
            
            if (result.success) {
                // Replace note content with extracted text
                const editor = document.getElementById('editor');
                const htmlContent = this.markdownToHtml(result.text);
                safeSetInnerHTML(editor, htmlContent);

                // Update current note
                this.currentNote.content = htmlContent;
                this.saveCurrentNote();
                
                this.updateFileUploadStatus(fileItem, 'success', 'Content inserted successfully');
                this.showNotification(`Content from ${result.filename} inserted into note`, 'success');
                
                // Close modal after a short delay
                setTimeout(() => {
                    this.hideUploadPdfModal();
                }, 1500);
            } else {
                this.updateFileUploadStatus(fileItem, 'error', 'Processing failed');
                this.showNotification('Error processing file', 'error');
            }
        } catch (error) {
            console.error('PDF upload error:', error);
            this.updateFileUploadStatus(fileItem, 'error', `Processing failed: ${error.message}`);
            this.showNotification('Error processing file', 'error');
        }
    }

    async uploadPdfFileWithProgress(file, fileItem) {
        const formData = new FormData();
        formData.append('file', file, file.name);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Set timeout for large files
            const timeoutId = setTimeout(() => {
                xhr.abort();
                reject(new Error('Upload timeout - file too large or connection too slow'));
            }, 5 * 60 * 1000); // 5 minutes timeout

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    const progressBar = fileItem.querySelector('.progress-bar');
                    const progressPercentage = fileItem.querySelector('.progress-percentage');
                    const statusElement = fileItem.querySelector('.file-upload-status');
                    
                    if (progressBar && progressPercentage && statusElement) {
                        progressBar.style.width = percentComplete + '%';
                        progressPercentage.textContent = Math.round(percentComplete) + '%';
                        
                        if (percentComplete < 100) {
                            statusElement.textContent = `Uploading... ${Math.round(percentComplete)}%`;
                        } else {
                            statusElement.textContent = 'Processing...';
                        }
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
                reject(new Error('Upload was aborted'));
            });
            
            xhr.open('POST', '/api/upload-pdf');
            if (authToken) xhr.setRequestHeader('Authorization', authToken);
            xhr.send(formData);
        });
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

    async loadConceptLanguagePreference() {
        try {
            const resp = await authFetch('/api/user-config', {
                method: 'GET'
            });
            
            if (resp.ok) {
                const data = await resp.json();
                const config = data.config || {};
                const conceptLanguage = config.conceptLanguage || 'en';
                const conceptLemmatization = config.conceptLemmatization ?? true;
                
                const languageSelect = document.getElementById('concept-language');
                if (languageSelect) {
                    languageSelect.value = conceptLanguage;
                }
                
                const lemmatizationToggle = document.getElementById('concept-lemmatization');
                if (lemmatizationToggle) {
                    lemmatizationToggle.checked = conceptLemmatization;
                }
            }
        } catch (error) {
            console.error('Error loading concept preferences:', error);
            // Default to English and enabled lemmatization if loading fails
            const languageSelect = document.getElementById('concept-language');
            if (languageSelect) {
                languageSelect.value = 'en';
            }
            const lemmatizationToggle = document.getElementById('concept-lemmatization');
            if (lemmatizationToggle) {
                lemmatizationToggle.checked = true;
            }
        }
    }

    async saveConceptLanguagePreference() {
        try {
            const languageSelect = document.getElementById('concept-language');
            const lemmatizationToggle = document.getElementById('concept-lemmatization');
            if (!languageSelect) return;
            
            const language = languageSelect.value;
            const lemmatization = lemmatizationToggle ? lemmatizationToggle.checked : true;
            
            // Load current config
            const resp = await authFetch('/api/user-config', {
                method: 'GET'
            });
            
            let config = {};
            if (resp.ok) {
                const data = await resp.json();
                config = data.config || {};
            }
            
            // Update concept preferences
            config.conceptLanguage = language;
            config.conceptLemmatization = lemmatization;
            
            // Save back to server
            await authFetch('/api/user-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            console.log('Concept preferences saved:', { language, lemmatization });
        } catch (error) {
            console.error('Error saving concept preferences:', error);
        }
    }

    async showConceptGraphModal() {
        const modal = document.getElementById('concept-graph-modal');
        const container = document.getElementById('concept-graph-container');
        const insightsEl = document.getElementById('map-insights');
        const nodeDetailsEl = document.getElementById('node-details');
        
        if (!modal || !container) return;
        
        // Load user's preferred concept language
        await this.loadConceptLanguagePreference();
        
        // Clear previous content
        container.innerHTML = '';
        insightsEl.innerHTML = '';
        nodeDetailsEl.innerHTML = '<p class="no-selection">Click on a node to view its details</p>';
        
        // Set up note scope functionality
        this.setupConceptNoteScope();
        
        // Set up regenerate button
        const regenerateBtn = document.getElementById('regenerate-concept-graph');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => {
                this.regenerateConceptGraph();
            });
        }
        
        // Set up AI reprocess button
        const aiReprocessBtn = document.getElementById('ai-reprocess-btn');
        if (aiReprocessBtn) {
            aiReprocessBtn.addEventListener('click', () => {
                this.reprocessGraphWithAI();
            });
        }
        
        // Set up AI suggestions button
        const aiSuggestionsBtn = document.getElementById('ai-suggestions-btn');
        if (aiSuggestionsBtn) {
            aiSuggestionsBtn.addEventListener('click', () => {
                this.showAISuggestionsWindow();
            });
        }
        
        // Set up AI generate nodes button
        const aiGenerateNodesBtn = document.getElementById('ai-generate-nodes-btn');
        if (aiGenerateNodesBtn) {
            aiGenerateNodesBtn.addEventListener('click', () => {
                this.generateAINodes();
            });
        }
        
        // Set up concept removal button
        const conceptRemovalBtn = document.getElementById('concept-removal-btn');
        if (conceptRemovalBtn) {
            conceptRemovalBtn.addEventListener('click', () => {
                this.showConceptRemovalModal();
            });
        }
        
        // Set up AI suggestions window functionality
        this.setupAISuggestionsWindow();
        
        // Set up concept removal modal functionality
        this.setupConceptRemovalModal();
        
        // Set up language selector change event
        const languageSelect = document.getElementById('concept-language');
        if (languageSelect) {
            languageSelect.addEventListener('change', () => {
                this.saveConceptLanguagePreference();
            });
        }
        
        // Set up lemmatization toggle change event
        const lemmatizationToggle = document.getElementById('concept-lemmatization');
        if (lemmatizationToggle) {
            lemmatizationToggle.addEventListener('change', () => {
                this.saveConceptLanguagePreference();
            });
        }
        
        // Show modal first, then generate graph
        modal.classList.add('active');
        this.hideMobileFab();
        
        // Generate initial graph
        await this.refreshConceptGraph();
    }

    async regenerateConceptGraph() {
        const container = document.getElementById('concept-graph-container');
        const insightsEl = document.getElementById('map-insights');
        const nodeDetailsEl = document.getElementById('node-details');
        
        if (!container) return;
        
        // Clear content
        container.innerHTML = '';
        insightsEl.innerHTML = '';
        nodeDetailsEl.innerHTML = '<p class="no-selection">Click on a node to view its details</p>';
        
        // Clear any manual positions from previous graph
        this.clearManualPositions();
        
        // Get text length for better progress indication
        const noteText = await this.getNotesContentForConcept();
        if (!noteText) {
            return;
        }
        
        const textLength = noteText.length;
        let progressMessage = 'Regenerating concept map...';
        
        if (textLength > 100000) {
            progressMessage = 'Processing large document... This may take a moment.';
        } else if (textLength > 50000) {
            progressMessage = 'Processing medium document... Please wait.';
        }
        
        this.showProcessingOverlay(progressMessage);
        
        try {
            const analysisType = document.getElementById('concept-analysis-type')?.value || 'bridges';
            const language = document.getElementById('concept-language')?.value || 'en';
            
            // Add timeout for large documents
            const timeoutMs = textLength > 100000 ? 45000 : 30000; // 45s for large, 30s for others
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
            
            const resp = await authFetch('/api/concept-graph', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({ 
                    note: noteText,
                    analysis_type: analysisType,
                    language: language
                })
            });
            
            clearTimeout(timeoutId);
            
            if (!resp.ok) {
                if (resp.status === 408) {
                    throw new Error('Processing timed out. Try using AI reprocessing or working with shorter text sections.');
                }
                throw new Error('Request failed');
            }
            
            const data = await resp.json();
            
            this.currentGraphData = data.graph;
            this.currentGraphInsights = data.insights;
            
            this.renderConceptGraph(data.graph);
            this.renderGraphInsights(data.insights);
        } catch (e) {
            if (e.name === 'AbortError') {
                this.showNotification('Processing timed out. Try using AI reprocessing or working with shorter text sections.', 'error');
            } else {
                this.showNotification(e.message || 'Regeneration failed', 'error');
            }
        } finally {
            this.hideProcessingOverlay();
        }
    }

    renderGraphInsights(insights) {
        const insightsEl = document.getElementById('map-insights');
        if (!insightsEl) return;
        
        const analysisTypeText = insights.analysis_type === 'bridges' ? 'Bridge Analysis' :
                                insights.analysis_type === 'hubs' ? 'Hub Analysis' :
                                insights.analysis_type === 'global' ? 'Global Analysis' :
                                'Local Analysis';
        
        const dominantLabel = insights.dominant_label || 'Key Concepts';
        
        insightsEl.innerHTML = `
            <div class="insight-item">
                <span class="insight-label">Analysis Type</span>
                <div class="insight-value">${analysisTypeText}</div>
            </div>
            
            <div class="insight-item">
                <span class="insight-label">Network Size</span>
                <div class="insight-value">${insights.total_nodes} nodes, ${insights.total_links} links</div>
            </div>
            
            <div class="insight-item">
                <span class="insight-label">Clusters</span>
                <div class="insight-value">${insights.total_clusters} connected groups</div>
            </div>
            
            <div class="insight-item">
                <span class="insight-label">${dominantLabel}</span>
                <div class="insight-tags">
                    ${insights.dominant_topics.map(topic => `<span class="insight-tag" data-node-label="${topic}">${topic}</span>`).join('')}
                </div>
            </div>
            
            <div class="insight-item">
                <span class="insight-label">Bridging Concepts</span>
                <div class="insight-tags">
                    ${insights.bridging_concepts.map(concept => `<span class="insight-tag insight-tag--secondary" data-node-label="${concept}">${concept}</span>`).join('')}
                </div>
            </div>
            
            <div class="insight-item">
                <span class="insight-label">Knowledge Gaps</span>
                <div class="insight-tags">
                    ${insights.knowledge_gaps.map(gap => `<span class="insight-tag insight-tag--warning" data-node-label="${gap}">${gap}</span>`).join('')}
                </div>
            </div>
            
            ${insights.centrality_threshold !== undefined ? `
                <div class="insight-item">
                    <span class="insight-label">Centrality Threshold</span>
                    <div class="insight-value">${insights.centrality_threshold.toFixed(4)}</div>
                </div>
            ` : ''}
        `;
        
        // Add click handlers for insight tags
        this.addInsightTagClickHandlers();
    }

    renderNodeDetails(node, connectedNodes = []) {
        const nodeDetailsEl = document.getElementById('node-details');
        if (!nodeDetailsEl) return;
        
        const connections = connectedNodes.length;
        const betweenness = node.betweenness_centrality || 0;
        const degree_centrality = node.degree_centrality || 0;
        const diversity = node.diversity || 0;
        const degree = node.degree || 0;
        
        // Group nodes by level for better display
        const nodesByLevel = {
            1: connectedNodes.filter(n => n.level === 1),
            2: connectedNodes.filter(n => n.level === 2),
            3: connectedNodes.filter(n => n.level === 3)
        };
        
        nodeDetailsEl.innerHTML = `
            <div class="node-title">${node.label}</div>
            
            <div class="node-metric">
                <span class="node-metric-label">Total Connections (3 levels)</span>
                <span class="node-metric-value">${connections}</span>
            </div>
            
            <div class="node-metric">
                <span class="node-metric-label">Direct Degree</span>
                <span class="node-metric-value">${degree}</span>
            </div>
            
            <div class="node-metric">
                <span class="node-metric-label">Betweenness Centrality</span>
                <span class="node-metric-value">${betweenness.toFixed(4)}</span>
            </div>
            
            <div class="node-metric">
                <span class="node-metric-label">Degree Centrality</span>
                <span class="node-metric-value">${degree_centrality.toFixed(4)}</span>
            </div>
            
            <div class="node-metric">
                <span class="node-metric-label">Diversity</span>
                <span class="node-metric-value">${diversity.toFixed(4)}</span>
            </div>
            
            <div class="node-metric">
                <span class="node-metric-label">Analysis Relevance</span>
                <span class="node-metric-value">${this.getNodeRelevanceLabel(node, betweenness, degree_centrality, diversity)}</span>
            </div>
            
            ${connections > 0 ? `
                <div class="connected-nodes">
                    <h5>Connected Nodes (3 levels deep)</h5>
                    
                    ${nodesByLevel[1].length > 0 ? `
                        <div class="level-group">
                            <h6 class="level-title">Level 1 - Direct (${nodesByLevel[1].length})</h6>
                            <div class="connected-list">
                                ${nodesByLevel[1].map(connectedNode => 
                                    `<span class="connected-node level-1" data-node-id="${connectedNode.id}">${connectedNode.label}</span>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${nodesByLevel[2].length > 0 ? `
                        <div class="level-group">
                            <h6 class="level-title">Level 2 - Secondary (${nodesByLevel[2].length})</h6>
                            <div class="connected-list">
                                ${nodesByLevel[2].map(connectedNode => 
                                    `<span class="connected-node level-2" data-node-id="${connectedNode.id}">${connectedNode.label}</span>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${nodesByLevel[3].length > 0 ? `
                        <div class="level-group">
                            <h6 class="level-title">Level 3 - Tertiary (${nodesByLevel[3].length})</h6>
                            <div class="connected-list">
                                ${nodesByLevel[3].map(connectedNode => 
                                    `<span class="connected-node level-3" data-node-id="${connectedNode.id}">${connectedNode.label}</span>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            ` : ''}
        `;
        
        // Add click handlers for connected nodes
        const connectedNodeElements = nodeDetailsEl.querySelectorAll('.connected-node');
        connectedNodeElements.forEach(el => {
            el.addEventListener('click', () => {
                const nodeId = el.dataset.nodeId;
                this.highlightNode(nodeId);
            });
        });
    }

    getNodeRelevanceLabel(node, betweenness, degree_centrality, diversity) {
        const analysisType = this.currentGraphInsights?.analysis_type || 'bridges';
        
        if (analysisType === 'bridges') {
            if (betweenness > 0.1) return "Strong Bridge";
            if (betweenness > 0.05) return "Moderate Bridge";
            return "Weak Bridge";
        } else if (analysisType === 'hubs') {
            if (degree_centrality > 0.2) return "Major Hub";
            if (degree_centrality > 0.1) return "Minor Hub";
            return "Peripheral";
        } else {
            const combined = (betweenness + degree_centrality) / 2;
            if (combined > 0.15) return "Highly Central";
            if (combined > 0.08) return "Moderately Central";
            return "Peripheral";
        }
    }

    highlightNode(nodeId) {
        // This will be called from connected node clicks
        // Find the node in the graph and simulate a click
        const nodeElement = d3.select('.concept-graph-container .nodes')
            .selectAll('.node')
            .filter(d => d.id == nodeId); // Use == to handle string/number comparison
        
        if (!nodeElement.empty()) {
            nodeElement.dispatch('click');
        }
    }

    highlightNodeByLabel(nodeLabel) {
        // Find the node in the current graph data by label and select it
        if (!this.currentGraphData || !this.currentGraphData.nodes) return;
        
        const node = this.currentGraphData.nodes.find(n => n.label === nodeLabel);
        if (!node) return;
        
        // Find the corresponding DOM element and simulate a click
        const nodeElement = d3.select('.concept-graph-container .nodes')
            .selectAll('.node')
            .filter(d => d.id === node.id);
        
        if (!nodeElement.empty()) {
            nodeElement.dispatch('click');
        }
    }

    addInsightTagClickHandlers() {
        // Add click handlers to all insight tags to select corresponding nodes
        const insightTags = document.querySelectorAll('.insight-tag[data-node-label]');
        insightTags.forEach(tag => {
            tag.addEventListener('click', (e) => {
                const nodeLabel = e.target.dataset.nodeLabel;
                if (nodeLabel) {
                    this.highlightNodeByLabel(nodeLabel);
                }
            });
        });
    }

    hideConceptGraphModal() {
        const modal = document.getElementById('concept-graph-modal');
        if (modal) modal.classList.remove('active');
        
        // Reset concept graph settings
        this.conceptNoteScope = 'current';
        this.conceptSelectedTags.clear();
        
        // Reset UI elements
        const scopeSelect = document.getElementById('concept-note-scope');
        const tagContainer = document.getElementById('tag-selection-container');
        if (scopeSelect) scopeSelect.value = 'current';
        if (tagContainer) tagContainer.classList.add('hidden');
        
        this.showMobileFab();
    }

    setupConceptNoteScope() {
        const scopeSelect = document.getElementById('concept-note-scope');
        const tagContainer = document.getElementById('tag-selection-container');
        const refreshBtn = document.getElementById('refresh-concept-graph');

        if (scopeSelect) {
            scopeSelect.addEventListener('change', () => {
                this.conceptNoteScope = scopeSelect.value;
                if (this.conceptNoteScope === 'tagged') {
                    tagContainer.classList.remove('hidden');
                    this.renderConceptTagFilter();
                } else {
                    tagContainer.classList.add('hidden');
                }
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshConceptGraph();
            });
        }
    }

    renderConceptTagFilter() {
        const container = document.getElementById('concept-tag-filter');
        if (!container) return;

        const allTags = this.gatherAllTags();
        if (allTags.length === 0) {
            container.innerHTML = '<p class="no-tags-message">No tags available</p>';
            return;
        }

        container.innerHTML = allTags.map(tag => `
            <div class="tag-checkbox-item">
                <input type="checkbox" id="concept-tag-${tag}" value="${tag}" ${this.conceptSelectedTags.has(tag) ? 'checked' : ''}>
                <label for="concept-tag-${tag}">${tag}</label>
            </div>
        `).join('');

        // Add event listeners
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const tag = e.target.value;
                if (e.target.checked) {
                    this.conceptSelectedTags.add(tag);
                } else {
                    this.conceptSelectedTags.delete(tag);
                }
            });
        });
    }

    async getNotesContentForConcept() {
        switch (this.conceptNoteScope) {
            case 'current':
                return this.getCurrentMarkdown();
            
            case 'all':
                let allContent = '';
                for (const note of this.notes) {
                    if (!note.loaded) {
                        await this.fetchNoteContent(note);
                        note.loaded = true;
                    }
                    allContent += `\n\n# ${note.title}\n${note.content}`;
                }
                return allContent;
            
            case 'tagged':
                if (this.conceptSelectedTags.size === 0) {
                    this.showNotification('Please select at least one tag', 'error');
                    return '';
                }
                
                let taggedContent = '';
                for (const note of this.notes) {
                    const noteTags = note.tags || [];
                    const hasSelectedTag = [...this.conceptSelectedTags].some(tag => noteTags.includes(tag));
                    
                    if (hasSelectedTag) {
                        if (!note.loaded) {
                            await this.fetchNoteContent(note);
                            note.loaded = true;
                        }
                        taggedContent += `\n\n# ${note.title}\n${note.content}`;
                    }
                }
                
                if (!taggedContent) {
                    this.showNotification('No notes found with selected tags', 'warning');
                    return '';
                }
                
                return taggedContent;
            
            default:
                return this.getCurrentMarkdown();
        }
    }

    async refreshConceptGraph() {
        const container = document.getElementById('concept-graph-container');
        const insightsEl = document.getElementById('map-insights');
        const nodeDetailsEl = document.getElementById('node-details');
        
        if (!container) return;
        
        // Clear content
        container.innerHTML = '';
        insightsEl.innerHTML = '';
        nodeDetailsEl.innerHTML = '<p class="no-selection">Click on a node to view its details</p>';
        
        // Clear any manual positions from previous graph
        this.clearManualPositions();
        
        this.showProcessingOverlay('Generating concept map...');
        
        try {
            const noteText = await this.getNotesContentForConcept();
            if (!noteText) {
                this.hideProcessingOverlay();
                return;
            }
            
            const analysisType = document.getElementById('concept-analysis-type')?.value || 'bridges';
            const language = document.getElementById('concept-language')?.value || 'en';
            const enableLemmatization = document.getElementById('concept-lemmatization')?.checked ?? true;
            
            const resp = await authFetch('/api/concept-graph', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    note: noteText,
                    analysis_type: analysisType,
                    language: language,
                    enable_lemmatization: enableLemmatization
                })
            });
            
            if (!resp.ok) throw new Error('Request failed');
            const data = await resp.json();
            
            this.currentGraphData = data.graph;
            this.currentGraphInsights = data.insights;
            
            this.renderConceptGraph(data.graph);
            this.renderGraphInsights(data.insights);
        } catch (e) {
            this.showNotification(e.message || 'Graph generation failed', 'error');
        } finally {
            this.hideProcessingOverlay();
        }
    }

    renderConceptGraph(graph) {
        const container = document.getElementById('concept-graph-container');
        if (!container) return;
        
        // Store original graph data for filtering
        this.originalGraphData = JSON.parse(JSON.stringify(graph));
        this.currentGraphData = graph;
        
        // Clear any existing content
        container.innerHTML = '';
        
        // Check if we have data
        if (!graph.nodes || graph.nodes.length === 0) {
            container.innerHTML = '<div class="no-graph-data">No concept graph data available. Try adding more content to your note.</div>';
            return;
        }

        const width = container.clientWidth || 800;
        const height = container.clientHeight || 600;
        
        // Create SVG with better styling
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .style('background', '#fafafa')
            .style('border-radius', '8px');
        
        // Add zoom and pan functionality with rotation support
        const g = svg.append('g');
        this.rotationAngle = 0; // Initialize rotation angle
        this.rotationMode = false; // Initialize rotation mode
        
        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                if (!this.rotationMode) {
                    g.attr('transform', event.transform);
                    // Update node and label visibility based on zoom level with consistent label sizing
                    this.updateNodeVisibilityOnZoom(event.transform.k);
                }
            });
        
        svg.call(zoom);
        
        // Add rotation drag behavior
        this.setupRotationDrag(svg, g, zoom);
        
        // Store references for filtering
        this.graphElements = {
            svg: svg,
            g: g,
            zoom: zoom,
            width: width,
            height: height,
            container: container
        };
        
        // Create integrated sliders inside the graph
        this.createIntegratedSliders(container);
        
        // Initial render
        this.updateGraphVisualization();
        
        // Add control panel
        this.addGraphControls(container, null, zoom, svg);
        
        // Setup sliders
        this.setupGraphSliders();
    }

    findConnectedNodesUpTo3Levels(centralNode, graph) {
        // Create adjacency list for efficient traversal
        const adjacencyList = {};
        graph.nodes.forEach(node => {
            adjacencyList[node.id] = [];
        });
        
        graph.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            
            if (adjacencyList[sourceId] && adjacencyList[targetId]) {
                adjacencyList[sourceId].push(targetId);
                adjacencyList[targetId].push(sourceId);
            }
        });
        
        // BFS to find nodes up to 3 levels deep
        const visited = new Set();
        const levelNodes = {
            0: [centralNode.id], // Central node (level 0)
            1: [], // First level connections
            2: [], // Second level connections
            3: []  // Third level connections
        };
        
        visited.add(centralNode.id);
        
        // Level 1: Direct connections
        const directConnections = adjacencyList[centralNode.id] || [];
        directConnections.forEach(nodeId => {
            if (!visited.has(nodeId)) {
                levelNodes[1].push(nodeId);
                visited.add(nodeId);
            }
        });
        
        // Level 2: Connections of level 1 nodes
        levelNodes[1].forEach(nodeId => {
            const connections = adjacencyList[nodeId] || [];
            connections.forEach(connectedNodeId => {
                if (!visited.has(connectedNodeId)) {
                    levelNodes[2].push(connectedNodeId);
                    visited.add(connectedNodeId);
                }
            });
        });
        
        // Level 3: Connections of level 2 nodes
        levelNodes[2].forEach(nodeId => {
            const connections = adjacencyList[nodeId] || [];
            connections.forEach(connectedNodeId => {
                if (!visited.has(connectedNodeId)) {
                    levelNodes[3].push(connectedNodeId);
                    visited.add(connectedNodeId);
                }
            });
        });
        
        // Convert node IDs back to node objects
        const allConnectedNodes = [];
        const nodeMap = {};
        graph.nodes.forEach(node => {
            nodeMap[node.id] = node;
        });
        
        // Add all levels (excluding central node)
        [1, 2, 3].forEach(level => {
            levelNodes[level].forEach(nodeId => {
                if (nodeMap[nodeId]) {
                    allConnectedNodes.push({
                        ...nodeMap[nodeId],
                        level: level // Add level information for potential UI differentiation
                    });
                }
            });
        });
        
        return {
            allConnectedNodes,
            levelNodes,
            centralNode
        };
    }

    updateGraphVisualization() {
        if (!this.graphElements || !this.currentGraphData) return;
        
        const { g, width, height } = this.graphElements;
        let graph = this.currentGraphData;
        
        // Clear existing elements
        g.selectAll("*").remove();
        
        // STEP 1: Calculate actual node degrees from the graph structure
        const nodeDegrees = {};
        graph.nodes.forEach(node => {
            nodeDegrees[node.id] = 0;
        });

        graph.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            
            if (nodeDegrees[sourceId] !== undefined) nodeDegrees[sourceId]++;
            if (nodeDegrees[targetId] !== undefined) nodeDegrees[targetId]++;
        });

        // STEP 2: Get current slider values for dynamic filtering
        const maxNodes = parseInt(document.getElementById('max-nodes-slider')?.value || '150');
        const minDegree = parseInt(document.getElementById('node-degree-slider')?.value || '3');
        const labelCount = parseInt(document.getElementById('label-count-slider')?.value || '50');

        // STEP 3: Filter nodes with degree >= minDegree, sort by degree, keep top maxNodes
        let filteredNodes = graph.nodes.filter(node => {
            const degree = nodeDegrees[node.id] || 0;
            return degree >= minDegree;
        });

        // Sort by degree (descending) and limit to maxNodes
        filteredNodes.sort((a, b) => (nodeDegrees[b.id] || 0) - (nodeDegrees[a.id] || 0));
        filteredNodes = filteredNodes.slice(0, maxNodes);

        // STEP 4: Create set of filtered node IDs and filter links
        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
        const filteredLinks = graph.links.filter(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            return filteredNodeIds.has(sourceId) && filteredNodeIds.has(targetId);
        });

        // Update graph with filtered data
        graph = { nodes: filteredNodes, links: filteredLinks };

        // STEP 5: Assign sizes based on degree and communities (with improved detection and fallback)
        const maxFilteredDegree = Math.max(...filteredNodes.map(n => nodeDegrees[n.id] || 0));
        const minFilteredDegree = Math.min(...filteredNodes.map(n => nodeDegrees[n.id] || 0));
        
        // Community detection with fallback
        let communities;
        try {
            communities = this.detectCommunities(graph);
            
            // Verify communities are properly distributed
            const uniqueCommunities = new Set(Object.values(communities));
            if (uniqueCommunities.size < 2) {
                throw new Error('Insufficient community diversity');
            }
        } catch (error) {
            console.warn('Community detection failed, using degree-based coloring:', error);
            // Fallback: assign communities based on degree ranges for color variety
            communities = {};
            filteredNodes.forEach(node => {
                const degree = nodeDegrees[node.id] || 0;
                communities[node.id] = Math.min(Math.floor(degree / 3), 6); // Max 7 color groups
            });
        }
        
        // Enhanced color palette with better contrast
        const communityColors = d3.scaleOrdinal()
            .domain([...new Set(Object.values(communities))])
            .range([
                '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
                '#1abc9c', '#e67e22', '#34495e', '#f1c40f', '#95a5a6',
                '#8e44ad', '#16a085', '#27ae60', '#2980b9', '#c0392b'
            ]);

        // STEP 6: Determine which nodes get labels (multi-tier approach + all AI nodes)
        const sortedNodesByDegree = [...filteredNodes]
            .sort((a, b) => (nodeDegrees[b.id] || 0) - (nodeDegrees[a.id] || 0));
        
        const labeledNodeIds = new Set();
        
        // Tier 1: Top nodes (largest - get priority labels)
        const tier1Count = Math.ceil(labelCount * 0.4); // 40% of label count for biggest nodes
        sortedNodesByDegree.slice(0, tier1Count).forEach(n => labeledNodeIds.add(n.id));
        
        // Tier 2: 2nd biggest nodes 
        const tier2Count = Math.ceil(labelCount * 0.3); // 30% for 2nd tier
        sortedNodesByDegree.slice(tier1Count, tier1Count + tier2Count).forEach(n => labeledNodeIds.add(n.id));
        
        // Tier 3: 3rd biggest nodes
        const tier3Count = Math.ceil(labelCount * 0.2); // 20% for 3rd tier
        sortedNodesByDegree.slice(tier1Count + tier2Count, tier1Count + tier2Count + tier3Count).forEach(n => labeledNodeIds.add(n.id));
        
        // Tier 4: 4th biggest nodes
        const tier4Count = labelCount - tier1Count - tier2Count - tier3Count; // Remaining for 4th tier
        if (tier4Count > 0) {
            sortedNodesByDegree.slice(tier1Count + tier2Count + tier3Count, tier1Count + tier2Count + tier3Count + tier4Count).forEach(n => labeledNodeIds.add(n.id));
        }
        
        // Always show labels for AI nodes
        filteredNodes.forEach(node => {
            if (node.isAIGenerated) {
                labeledNodeIds.add(node.id);
            }
        });

        // Assign properties to nodes
        filteredNodes.forEach(node => {
            const degree = nodeDegrees[node.id] || 0;
            // Size nodes by degree (range: 4-20), AI nodes get larger size
            if (node.isAIGenerated) {
                node.calculatedSize = Math.max(18, node.importance * 25);
            } else {
                node.calculatedSize = 4 + ((degree - minFilteredDegree) / (maxFilteredDegree - minFilteredDegree)) * 16;
            }
            node.community = communities[node.id] || 0;
            node.showLabel = labeledNodeIds.has(node.id);
            node.degree = degree;
        });
        
        // STEP 7: Create enhanced links with variable width and special styling for AI connections
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(graph.links)
            .enter().append('line')
            .attr('class', d => d.isAIGenerated ? 'ai-connection' : 'regular-connection')
            .attr('stroke', d => d.isAIGenerated ? '#8b5cf6' : '#666')
            .attr('stroke-opacity', d => d.isAIGenerated ? 0.8 : 0.3)
            .attr('stroke-width', d => {
                if (d.isAIGenerated) {
                    return 2.5; // Thicker lines for AI connections
                }
                // Vary link width based on connected node degrees for regular connections
                const sourceDegree = nodeDegrees[typeof d.source === 'object' ? d.source.id : d.source] || 0;
                const targetDegree = nodeDegrees[typeof d.target === 'object' ? d.target.id : d.target] || 0;
                return Math.max(0.5, Math.min(3, (sourceDegree + targetDegree) / 20));
            })
            .attr('stroke-dasharray', d => d.isAIGenerated ? '5,3' : 'none')
            .style('cursor', 'pointer');
        
        // STEP 8: Create nodes with community colors and degree-based sizing
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(graph.nodes)
            .enter().append('g')
            .attr('class', 'node')
            .style('cursor', 'pointer');
        
        // Add shapes to nodes
        node.each(function(d) {
            const nodeGroup = d3.select(this);
            const radius = d.calculatedSize;
            
            if (d.isAIGenerated) {
                // Circle with AI styling for AI nodes
                nodeGroup.append('circle')
                    .attr('class', 'ai-node')
                    .attr('r', radius)
                    .attr('fill', '#e5e7ff')
                    .attr('stroke', '#8b5cf6')
                    .attr('stroke-width', 3);
            } else {
                // Circle for regular nodes, colored by community
                const communityColor = communityColors(d.community);
                d._color = communityColor;
                
                nodeGroup.append('circle')
                    .attr('r', radius)
                    .attr('fill', communityColor)
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2);
            }
        });
        
        // STEP 8: Add enhanced hover effects
        node.on('mouseover', function(event, d) {
            const nodeGroup = d3.select(this);
            const shape = nodeGroup.select(d.isAIGenerated ? 'path' : 'circle');
            
            // Scale up the shape on hover
            nodeGroup.transition()
                .duration(150)
                .attr('transform', `translate(${d.x},${d.y}) scale(1.4)`);
            
            shape.attr('stroke-width', 4)
                .attr('stroke', '#333');
            
            // Highlight connected nodes and links
            const connectedNodes = new Set([d.id]);
            link.style('stroke-opacity', l => {
                const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                if (sourceId === d.id || targetId === d.id) {
                    connectedNodes.add(sourceId);
                    connectedNodes.add(targetId);
                    return 0.8;
                }
                return 0.1;
            }).style('stroke', l => {
                const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                return (sourceId === d.id || targetId === d.id) ? '#333' : '#666';
            });
            
            node.style('opacity', n => connectedNodes.has(n.id) ? 1 : 0.2);
            
            // Show degree info in a tooltip-like manner
            if (d.showLabel) {
                const tooltip = g.append('text')
                    .attr('class', 'tooltip')
                    .attr('x', d.x + d.calculatedSize + 5)
                    .attr('y', d.y - 5)
                    .attr('font-size', '12px')
                    .attr('font-weight', 'bold')
                    .attr('fill', '#333')
                    .style('pointer-events', 'none')
                    .text(`${d.label} (degree: ${d.degree})`);
            }
        })
        .on('mouseout', function(event, d) {
            const nodeGroup = d3.select(this);
            const shape = nodeGroup.select(d.isAIGenerated ? 'path' : 'circle');
            
            // Reset scale
            nodeGroup.transition()
                .duration(150)
                .attr('transform', `translate(${d.x},${d.y}) scale(1)`);
            
            shape.attr('stroke-width', 2)
                .attr('stroke', '#fff');
            
            // Reset highlighting
            link.style('stroke-opacity', 0.3)
                .style('stroke', '#666');
            node.style('opacity', 1);
            
            // Remove tooltip
            g.selectAll('.tooltip').remove();
        });

        // STEP 9: Drag behavior functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // Apply drag behavior to nodes
        node.call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));
        
        // STEP 10: Add labels with white backgrounds (only for top nodes by degree or AI nodes)
        const labelGroup = g.append('g').attr('class', 'labels');
        
        const labelData = graph.nodes.filter(d => d.showLabel);
        
        // Create label backgrounds (white rectangles)
        const labelBg = labelGroup
            .selectAll('.label-bg')
            .data(labelData)
            .enter().append('rect')
            .attr('class', 'label-bg')
            .attr('fill', 'rgba(255, 255, 255, 0.9)')
            .attr('stroke', 'rgba(0, 0, 0, 0.1)')
            .attr('stroke-width', 0.5)
            .attr('rx', 2)
            .attr('ry', 2)
            .style('pointer-events', 'none');
        
        // Create label text with improved sizing
        const label = labelGroup
            .selectAll('text')
            .data(labelData)
            .enter().append('text')
            .attr('class', d => d.isAIGenerated ? 'ai-node-label' : 'regular-node-label')
            .attr('font-size', d => {
                // Improved font sizing - capped and more reasonable
                const baseSize = d.isAIGenerated ? 12 : 11;
                const sizeBonus = Math.min(4, (d.calculatedSize - 8) * 0.2); // Much smaller bonus
                return Math.max(9, Math.min(14, baseSize + sizeBonus)); // Capped between 9-14px
            })
            .attr('font-weight', d => d.isAIGenerated ? '700' : '600')
            .attr('dx', d => d.calculatedSize + 8)
            .attr('dy', '0.35em')
            .attr('fill', d => d.isAIGenerated ? '#6b46c1' : '#333')
            .attr('text-anchor', 'start')
            .style('pointer-events', 'none')
            .text(d => d.label);
        
        // Position label backgrounds after text is created
        labelBg.each(function(d, i) {
            const textElement = label.nodes()[i];
            if (textElement) {
                const bbox = textElement.getBBox();
                d3.select(this)
                    .attr('x', bbox.x - 2)
                    .attr('y', bbox.y - 1)
                    .attr('width', bbox.width + 4)
                    .attr('height', bbox.height + 2);
            }
        });
        
        // STEP 11: Implement stable simulation with balanced forces
        const simulation = d3.forceSimulation(graph.nodes)
            .force('link', d3.forceLink(graph.links)
                .id(d => d.id)
                .distance(d => {
                    // Moderate link distance based on node sizes
                    const sourceSize = d.source.calculatedSize || 8;
                    const targetSize = d.target.calculatedSize || 8;
                    return 50 + (sourceSize + targetSize) * 1.5;
                })
                .strength(0.5)
            )
            .force('charge', d3.forceManyBody()
                .strength(d => {
                    // Moderate repulsion to prevent excessive vibration
                    const baseDegree = d.degree || 1;
                    return -300 - (baseDegree * 20); // Reduced repulsion for stability
                })
                .distanceMin(10)
                .distanceMax(200)
            )
            .force('center', d3.forceCenter(width / 2, height / 2)
                .strength(0.1) // Moderate centering force
            )
            .force('collision', d3.forceCollide()
                .radius(d => d.calculatedSize + 8) // Reduced collision padding
                .strength(0.7)
                .iterations(2)
            )
            .alphaDecay(0.05) // Faster cooling to reduce vibration
            .velocityDecay(0.6); // Higher velocity decay for stability
        
        // STEP 12: Update positions on each tick with stabilization
        let tickCount = 0;
        simulation.on('tick', () => {
            tickCount++;
            
            // Update link positions
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            // Update node positions
            node.attr('transform', d => `translate(${d.x},${d.y})`);
            
            // Update label positions (both text and backgrounds)
            label
                .attr('x', d => d.x + (d.calculatedSize || 8) + 8)
                .attr('y', d => d.y);
            
            // Update label background positions
            labelBg.each(function(d, i) {
                const textElement = label.nodes()[i];
                if (textElement) {
                    try {
                        const bbox = textElement.getBBox();
                        d3.select(this)
                            .attr('x', bbox.x - 2)
                            .attr('y', bbox.y - 1)
                            .attr('width', bbox.width + 4)
                            .attr('height', bbox.height + 2);
                    } catch (e) {
                        // Fallback positioning if getBBox fails
                        d3.select(this)
                            .attr('x', d.x + (d.calculatedSize || 8) + 6)
                            .attr('y', d.y - 8)
                            .attr('width', d.label ? d.label.length * 6 + 4 : 20)
                            .attr('height', 16);
                    }
                }
            });
            
            // Stabilize after initial layout
            if (tickCount > 100) {
                simulation.alphaTarget(0.01); // Very low target to minimize movement
            }
        });
        
        // STEP 13: Click to highlight connections and show node details (with 3-level deep analysis)
        node.on('click', (event, d) => {
            event.stopPropagation();
            
            // Find connected nodes up to 3 levels deep for node details
            const connectionResult = this.findConnectedNodesUpTo3Levels(d, graph);
            const allConnectedNodes = connectionResult.allConnectedNodes;
            
            // For visual highlighting, only show direct connections (level 1)
            const connectedNodes = new Set([d.id]);
            const directlyConnectedNodes = allConnectedNodes.filter(n => n.level === 1);
            
            // Add direct connection IDs to the set for visual highlighting
            directlyConnectedNodes.forEach(node => {
                connectedNodes.add(node.id);
            });
            
            // Render node details with all 3 levels of connections
            this.renderNodeDetails(d, allConnectedNodes);
            
            // Visual feedback - highlight only directly connected nodes (same as hover)
            node.style('opacity', n => connectedNodes.has(n.id) ? 1 : 0.2);
            
            // Highlight only links that connect to the clicked node
            link.style('stroke-opacity', l => {
                const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                return (sourceId === d.id || targetId === d.id) ? 0.8 : 0.1;
            }).style('stroke-width', l => {
                const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                return (sourceId === d.id || targetId === d.id) ? 3 : 1;
            });
            
            // Only show labels and backgrounds for connected nodes
            label.style('opacity', n => connectedNodes.has(n.id) ? 1 : 0.3);
            labelBg.style('opacity', n => connectedNodes.has(n.id) ? 0.9 : 0.2);
        });
        
        // STEP 14: Click on background to reset
        this.graphElements.svg.on('click', (event) => {
            if (event.target === this.graphElements.svg.node()) {
                // Reset highlighting
                node.style('opacity', 1);
                link.style('stroke-opacity', 0.3)
                    .style('stroke-width', d => {
                        // Restore original width based on degree
                        const sourceDegree = nodeDegrees[typeof d.source === 'object' ? d.source.id : d.source] || 0;
                        const targetDegree = nodeDegrees[typeof d.target === 'object' ? d.target.id : d.target] || 0;
                        return Math.max(0.5, Math.min(3, (sourceDegree + targetDegree) / 20));
                    });
                label.style('opacity', 1);
                labelBg.style('opacity', 0.9);
                
                // Reset node details panel
                const nodeDetailsEl = document.getElementById('node-details');
                if (nodeDetailsEl) {
                    nodeDetailsEl.innerHTML = '<p class="no-selection">Click on a node to view its details</p>';
                }
            }
        });
        
        // Store simulation for later use
        this.graphElements.simulation = simulation;
        this.graphElements.nodes = node;
        this.graphElements.links = link;
        this.graphElements.labels = label;
        this.graphElements.labelBg = labelBg;
        this.graphElements.labelGroup = labelGroup;
        
        // Update drag behavior based on current mode
        this.updateNodeDragBehavior();
        
        // Initialize node visibility for default zoom level
        this.updateNodeVisibilityOnZoom(1.0);
    }

    // Improved community detection using modularity-based clustering
    detectCommunities(graph) {
        const communities = {};
        const adjacencyList = {};
        
        // Initialize each node in its own community and build adjacency list
        graph.nodes.forEach(node => {
            communities[node.id] = node.id;
            adjacencyList[node.id] = new Set();
        });
        
        // Build adjacency list from links
        graph.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            
            if (adjacencyList[sourceId] && adjacencyList[targetId]) {
                adjacencyList[sourceId].add(targetId);
                adjacencyList[targetId].add(sourceId);
            }
        });
        
        // Simple agglomerative clustering based on connectivity
        let improved = true;
        let iterations = 0;
        const maxIterations = 10;
        
        while (improved && iterations < maxIterations) {
            improved = false;
            iterations++;
            
            Object.keys(communities).forEach(nodeId => {
                const currentCommunity = communities[nodeId];
                const neighbors = Array.from(adjacencyList[nodeId] || []);
                
                if (neighbors.length === 0) return;
                
                // Count connections to different communities
                const communityConnections = {};
                neighbors.forEach(neighborId => {
                    const neighborCommunity = communities[neighborId];
                    communityConnections[neighborCommunity] = (communityConnections[neighborCommunity] || 0) + 1;
                });
                
                // Find the community with the most connections
                let bestCommunity = currentCommunity;
                let maxConnections = communityConnections[currentCommunity] || 0;
                
                Object.entries(communityConnections).forEach(([community, connections]) => {
                    if (connections > maxConnections) {
                        maxConnections = connections;
                        bestCommunity = community;
                    }
                });
                
                // Move to better community if beneficial
                if (bestCommunity !== currentCommunity && maxConnections > 1) {
                    communities[nodeId] = bestCommunity;
                    improved = true;
                }
            });
        }
        
        // Renumber communities starting from 0
        const uniqueCommunities = [...new Set(Object.values(communities))];
        const communityMapping = {};
        uniqueCommunities.forEach((community, index) => {
            communityMapping[community] = index;
        });
        
        // Apply new community numbers
        const finalCommunities = {};
        Object.entries(communities).forEach(([nodeId, community]) => {
            finalCommunities[nodeId] = communityMapping[community];
        });
        
        console.log(`Detected ${uniqueCommunities.length} communities`);
        return finalCommunities;
    }

    createIntegratedSliders(container) {
        // Create slider container inside the graph (like the top controls but at bottom)
        const sliderContainer = d3.select(container)
            .append('div')
            .attr('class', 'graph-controls-bottom')
            .style('position', 'absolute')
            .style('bottom', '10px')
            .style('left', '50%')
            .style('transform', 'translateX(-50%)')
            .style('background', 'rgba(255, 255, 255, 0.95)')
            .style('border', '1px solid var(--color-border)')
            .style('border-radius', 'var(--radius-md)')
            .style('padding', 'var(--space-12) var(--space-16)')
            .style('display', 'flex')
            .style('gap', 'var(--space-20)')
            .style('align-items', 'center')
            .style('box-shadow', '0 4px 20px rgba(0, 0, 0, 0.1)')
            .style('backdrop-filter', 'blur(10px)')
            .style('z-index', '1000')
            .style('flex-wrap', 'wrap')
            .style('justify-content', 'center');

        // Max Nodes slider - Updated for selective approach
        const maxNodesControl = sliderContainer.append('div')
            .attr('class', 'slider-control')
            .style('display', 'flex')
            .style('flex-direction', 'column')
            .style('align-items', 'center')
            .style('gap', 'var(--space-4)')
            .style('min-width', '120px');
        
        maxNodesControl.append('label')
            .attr('for', 'max-nodes-slider')
            .style('font-size', 'var(--font-size-sm)')
            .style('font-weight', '500')
            .style('color', 'var(--color-text)')
            .style('white-space', 'nowrap')
            .html('Max Nodes: <span id="max-nodes-value">150</span>');
            
        maxNodesControl.append('input')
            .attr('type', 'range')
            .attr('id', 'max-nodes-slider')
            .attr('min', '50')
            .attr('max', '300')
            .attr('value', '150')
            .attr('step', '25')
            .style('width', '100px')
            .style('height', '4px')
            .style('border-radius', '2px')
            .style('background', 'var(--color-border)')
            .style('outline', 'none')
            .style('-webkit-appearance', 'none')
            .style('appearance', 'none');

        // Min Node Degree slider - Updated for selective filtering
        const nodeDegreeControl = sliderContainer.append('div')
            .attr('class', 'slider-control')
            .style('display', 'flex')
            .style('flex-direction', 'column')
            .style('align-items', 'center')
            .style('gap', 'var(--space-4)')
            .style('min-width', '120px');
        
        nodeDegreeControl.append('label')
            .attr('for', 'node-degree-slider')
            .style('font-size', 'var(--font-size-sm)')
            .style('font-weight', '500')
            .style('color', 'var(--color-text)')
            .style('white-space', 'nowrap')
            .html('Min Node Degree: <span id="node-degree-value">3</span>');
            
        nodeDegreeControl.append('input')
            .attr('type', 'range')
            .attr('id', 'node-degree-slider')
            .attr('min', '1')
            .attr('max', '15')
            .attr('value', '3')
            .attr('step', '1')
            .style('width', '100px')
            .style('height', '4px')
            .style('border-radius', '2px')
            .style('background', 'var(--color-border)')
            .style('outline', 'none')
            .style('-webkit-appearance', 'none')
            .style('appearance', 'none');

        // Label Count slider - New control for top N labels
        const labelCountControl = sliderContainer.append('div')
            .attr('class', 'slider-control')
            .style('display', 'flex')
            .style('flex-direction', 'column')
            .style('align-items', 'center')
            .style('gap', 'var(--space-4)')
            .style('min-width', '120px');
        
        labelCountControl.append('label')
            .attr('for', 'label-count-slider')
            .style('font-size', 'var(--font-size-sm)')
            .style('font-weight', '500')
            .style('color', 'var(--color-text)')
            .style('white-space', 'nowrap')
            .html('Label Count: <span id="label-count-value">50</span>');
            
        labelCountControl.append('input')
            .attr('type', 'range')
            .attr('id', 'label-count-slider')
            .attr('min', '10')
            .attr('max', '100')
            .attr('value', '50')
            .attr('step', '5')
            .style('width', '100px')
            .style('height', '4px')
            .style('border-radius', '2px')
            .style('background', 'var(--color-border)')
            .style('outline', 'none')
            .style('-webkit-appearance', 'none')
            .style('appearance', 'none');

        // Apply CSS custom properties for slider thumbs (since D3 doesn't handle pseudo-elements)
        const style = document.createElement('style');
        style.textContent = `
            .graph-controls-bottom input[type="range"]::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: var(--color-primary);
                cursor: pointer;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            
            .graph-controls-bottom input[type="range"]::-moz-range-thumb {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: var(--color-primary);
                cursor: pointer;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            
            .graph-controls-bottom input[type="range"]::-webkit-slider-track {
                background: var(--color-border);
                height: 4px;
                border-radius: 2px;
            }
            
            .graph-controls-bottom input[type="range"]::-moz-range-track {
                background: var(--color-border);
                height: 4px;
                border-radius: 2px;
                border: none;
            }
            
            @media (prefers-color-scheme: dark) {
                .graph-controls-bottom {
                    background: rgba(38, 40, 40, 0.95) !important;
                    border-color: var(--color-border) !important;
                }
            }
            
            [data-color-scheme="dark"] .graph-controls-bottom {
                background: rgba(38, 40, 40, 0.95) !important;
                border-color: var(--color-border) !important;
            }
        `;
        document.head.appendChild(style);
    }

    setupRotationDrag(svg, g, zoom) {
        let isDragging = false;
        let startAngle = 0;
        
        const dragBehavior = d3.drag()
            .on('start', (event) => {
                if (!this.rotationMode) return;
                isDragging = true;
                const rect = svg.node().getBoundingClientRect();
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                startAngle = Math.atan2(event.y - centerY, event.x - centerX);
            })
            .on('drag', (event) => {
                if (!this.rotationMode || !isDragging) return;
                event.sourceEvent.preventDefault();
                
                const rect = svg.node().getBoundingClientRect();
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const currentAngle = Math.atan2(event.y - centerY, event.x - centerX);
                const deltaAngle = currentAngle - startAngle;
                
                this.rotationAngle += deltaAngle * (180 / Math.PI);
                startAngle = currentAngle;
                
                // Apply rotation transform
                const currentTransform = d3.zoomTransform(svg.node());
                g.attr('transform', `${currentTransform} rotate(${this.rotationAngle}, ${centerX}, ${centerY})`);
            })
            .on('end', () => {
                isDragging = false;
            });
        
        svg.call(dragBehavior);
    }

    setupGraphSliders() {
        // Get slider elements 
        const maxNodesSlider = document.getElementById('max-nodes-slider');
        const nodeDegreeSlider = document.getElementById('node-degree-slider');
        const labelCountSlider = document.getElementById('label-count-slider');
        
        const maxNodesValue = document.getElementById('max-nodes-value');
        const nodeDegreeValue = document.getElementById('node-degree-value');
        const labelCountValue = document.getElementById('label-count-value');

        if (!maxNodesSlider || !nodeDegreeSlider || !labelCountSlider) return;

        // Set up event listeners with new approach
        maxNodesSlider.addEventListener('input', (e) => {
            maxNodesValue.textContent = e.target.value;
            this.applyGraphFilters();
        });

        nodeDegreeSlider.addEventListener('input', (e) => {
            nodeDegreeValue.textContent = e.target.value;
            this.applyGraphFilters();
        });

        labelCountSlider.addEventListener('input', (e) => {
            labelCountValue.textContent = e.target.value;
            this.applyGraphFilters();
        });
        
        // Set initial values to match the current selective approach
        console.log('Concept Graph: Using selective filtering approach (degree ≥ 3, top ~150 nodes, labels for top 50)');
    }

    applyGraphFilters() {
        // Since the filtering is now done directly in updateGraphVisualization,
        // this method just triggers a re-render with new slider values
        if (!this.originalGraphData) return;
        
        // The filtering logic is now integrated into updateGraphVisualization
        // which uses the slider values directly for:
        // 1. maxNodes: limits the top N nodes by degree (default 150)
        // 2. minDegree: minimum degree threshold (default 3)
        // 3. labelCount: number of labels to show for highest-degree nodes (default 50)
        
        this.updateGraphVisualization();
    }
    
    addGraphControls(container, simulation, zoom, svg) {
        // Create controls panel
        const controls = d3.select(container)
            .append('div')
            .attr('class', 'graph-controls')
            .style('position', 'absolute')
            .style('top', '10px')
            .style('right', '10px')
            .style('background', 'rgba(255, 255, 255, 0.9)')
            .style('padding', '10px')
            .style('border-radius', '5px')
            .style('box-shadow', '0 2px 10px rgba(0,0,0,0.1)')
            .style('z-index', '1000');
        
        // Zoom controls
        controls.append('button')
            .html('<i class="fas fa-search-plus"></i>')
            .attr('title', 'Zoom In')
            .style('margin', '2px')
            .style('padding', '5px 8px')
            .style('border', '1px solid #ccc')
            .style('background', '#fff')
            .style('cursor', 'pointer')
            .style('border-radius', '3px')
            .on('click', () => {
                svg.transition().call(zoom.scaleBy, 1.5);
            });
        
        controls.append('button')
            .html('<i class="fas fa-search-minus"></i>')
            .attr('title', 'Zoom Out')
            .style('margin', '2px')
            .style('padding', '5px 8px')
            .style('border', '1px solid #ccc')
            .style('background', '#fff')
            .style('cursor', 'pointer')
            .style('border-radius', '3px')
            .on('click', () => {
                svg.transition().call(zoom.scaleBy, 1 / 1.5);
            });
        
        controls.append('br');
        
        // Manual drag toggle button
        const dragButton = controls.append('button')
            .html('<i class="fas fa-arrows-alt"></i>')
            .attr('title', 'Manual Drag Mode')
            .attr('id', 'manual-drag-btn')
            .style('margin', '2px')
            .style('padding', '5px 8px')
            .style('border', '1px solid #ccc')
            .style('background', '#fff')
            .style('cursor', 'pointer')
            .style('border-radius', '3px')
            .on('click', () => {
                this.toggleManualDragMode(dragButton);
            });
        
        // Reset controls
        controls.append('button')
            .html('<i class="fas fa-compress-arrows-alt"></i>')
            .attr('title', 'Reset View')
            .style('margin', '2px')
            .style('padding', '5px 8px')
            .style('border', '1px solid #ccc')
            .style('background', '#fff')
            .style('cursor', 'pointer')
            .style('border-radius', '3px')
            .on('click', () => {
                svg.transition().call(zoom.transform, d3.zoomIdentity);
            });
        
        controls.append('button')
            .html('<i class="fas fa-sync"></i>')
            .attr('title', 'Restart Simulation')
            .style('margin', '2px')
            .style('padding', '5px 8px')
            .style('border', '1px solid #ccc')
            .style('background', '#fff')
            .style('cursor', 'pointer')
            .style('border-radius', '3px')
            .on('click', () => {
                if (this.graphElements && this.graphElements.simulation) {
                    // Clear manual positions when restarting simulation
                    this.clearManualPositions();
                    this.graphElements.simulation.alpha(1).restart();
                }
            });
    }

    toggleManualDragMode(dragButton) {
        // Initialize manual drag mode if not set
        if (this.manualDragMode === undefined) {
            this.manualDragMode = false;
        }
        
        // Toggle the mode
        this.manualDragMode = !this.manualDragMode;
        
        // Update button appearance
        if (this.manualDragMode) {
            dragButton.style('background', '#007acc')
                     .style('color', '#fff')
                     .style('border-color', '#007acc');
        } else {
            dragButton.style('background', '#fff')
                     .style('color', '#333')
                     .style('border-color', '#ccc');
        }
        
        // Update node drag behavior
        this.updateNodeDragBehavior();
    }

    updateNodeDragBehavior() {
        if (!this.graphElements || !this.graphElements.g) return;
        
        const nodes = this.graphElements.g.selectAll('.node');
        
        if (this.manualDragMode) {
            // Enable manual drag mode - nodes and connections stay where dropped
            nodes.call(d3.drag()
                .on('start', (event, d) => {
                    // Stop the simulation while dragging
                    if (this.graphElements.simulation) {
                        this.graphElements.simulation.stop();
                    }
                    
                    // Store initial position
                    d.startX = d.x;
                    d.startY = d.y;
                    
                    // Mark node as being manually positioned
                    d.isManuallyPositioned = true;
                })
                .on('drag', (event, d) => {
                    // Update node position
                    d.x = event.x;
                    d.y = event.y;
                    
                    // Fix the position so simulation doesn't override it
                    d.fx = event.x;
                    d.fy = event.y;
                    
                    // Update visual position immediately
                    this.updateNodePosition(d);
                })
                .on('end', (event, d) => {
                    // Keep the node fixed at the dropped position
                    d.fx = event.x;
                    d.fy = event.y;
                    
                    // Update connected nodes if they should follow
                    this.updateConnectedNodesPosition(d, event.x - d.startX, event.y - d.startY);
                })
            );
        } else {
            // Regular drag mode - simulation controls positions
            nodes.call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active && this.graphElements.simulation) {
                        this.graphElements.simulation.alphaTarget(0.3).restart();
                    }
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active && this.graphElements.simulation) {
                        this.graphElements.simulation.alphaTarget(0);
                    }
                    d.fx = null;
                    d.fy = null;
                })
            );
        }
    }

    updateNodePosition(node) {
        if (!this.graphElements || !this.graphElements.g) return;
        
        // Update node visual position
        const nodeElements = this.graphElements.g.selectAll('.node');
        nodeElements.each(function(d) {
            if (d.id === node.id) {
                d3.select(this).attr('transform', `translate(${d.x},${d.y}) scale(1)`);
            }
        });
        
        // Update connected links
        const linkElements = this.graphElements.g.selectAll('.links line');
        linkElements.each(function(l) {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            
            if (sourceId === node.id || targetId === node.id) {
                d3.select(this)
                    .attr('x1', l.source.x)
                    .attr('y1', l.source.y)
                    .attr('x2', l.target.x)
                    .attr('y2', l.target.y);
            }
        });
        
        // Update labels and label backgrounds
        const labelElements = this.graphElements.g.selectAll('.labels text');
        const labelBgElements = this.graphElements.g.selectAll('.label-bg');
        
        labelElements.each(function(d, i) {
            if (d.id === node.id) {
                const labelElement = d3.select(this);
                labelElement
                    .attr('x', d.x + (d.calculatedSize || 8) + 8)
                    .attr('y', d.y);
                
                // Update corresponding background
                const bgElement = d3.select(labelBgElements.nodes()[i]);
                if (!bgElement.empty()) {
                    try {
                        const bbox = labelElement.node().getBBox();
                        bgElement
                            .attr('x', bbox.x - 2)
                            .attr('y', bbox.y - 1)
                            .attr('width', bbox.width + 4)
                            .attr('height', bbox.height + 2);
                    } catch (e) {
                        // Fallback positioning
                        bgElement
                            .attr('x', d.x + (d.calculatedSize || 8) + 6)
                            .attr('y', d.y - 8)
                            .attr('width', d.label ? d.label.length * 6 + 4 : 20)
                            .attr('height', 16);
                    }
                }
            }
        });
    }

    updateConnectedNodesPosition(draggedNode, deltaX, deltaY) {
        if (!this.currentGraphData || !this.manualDragMode) return;
        
        // Find connected nodes
        const connectedNodeIds = new Set();
        this.currentGraphData.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            
            if (sourceId === draggedNode.id) {
                connectedNodeIds.add(targetId);
            }
            if (targetId === draggedNode.id) {
                connectedNodeIds.add(sourceId);
            }
        });
        
        // Move connected nodes by a fraction of the drag distance
        const followFactor = 0.3; // 30% of the drag distance
        
        this.currentGraphData.nodes.forEach(node => {
            if (connectedNodeIds.has(node.id) && !node.isManuallyPositioned) {
                node.x += deltaX * followFactor;
                node.y += deltaY * followFactor;
                node.fx = node.x;
                node.fy = node.y;
                
                this.updateNodePosition(node);
            }
        });
    }

    clearManualPositions() {
        if (!this.currentGraphData) return;
        
        // Clear all manual positioning flags and fixed positions
        this.currentGraphData.nodes.forEach(node => {
            node.isManuallyPositioned = false;
            node.fx = null;
            node.fy = null;
        });
        
        // Reset manual drag mode
        this.manualDragMode = false;
        
        // Reset button appearance
        const dragButton = d3.select('#manual-drag-btn');
        if (!dragButton.empty()) {
            dragButton.style('background', '#fff')
                     .style('color', '#333')
                     .style('border-color', '#ccc');
        }
    }

    updateNodeVisibilityOnZoom(zoomScale) {
        if (!this.graphElements || !this.graphElements.g) return;
        
        const nodes = this.graphElements.g.selectAll('.node');
        const labels = this.graphElements.g.selectAll('.labels text');
        
        // Calculate minimum size multiplier based on zoom level
        // At low zoom levels (0.1-0.5), make smaller nodes more visible
        // At high zoom levels (1.5-3), maintain original sizes or slightly enhance them
        const minSizeMultiplier = Math.max(1, Math.min(3, 1 / Math.pow(zoomScale, 0.7)));
        
        // Update node sizes based on zoom level
        nodes.each(function(d) {
            const nodeGroup = d3.select(this);
            const originalRadius = d.size || 8;
            const adjustedRadius = Math.max(4, originalRadius * minSizeMultiplier);
            
            if (d.isAIGenerated) {
                // Update pentagon size for AI nodes
                const pentagon = [];
                for (let i = 0; i < 5; i++) {
                    const angle = (i * 2 * Math.PI / 5) - Math.PI / 2;
                    const x = adjustedRadius * Math.cos(angle);
                    const y = adjustedRadius * Math.sin(angle);
                    pentagon.push([x, y]);
                }
                const pathData = `M${pentagon.map(p => p.join(',')).join('L')}Z`;
                nodeGroup.select('path').attr('d', pathData);
            } else {
                // Update circle radius for regular nodes
                nodeGroup.select('circle').attr('r', adjustedRadius);
            }
        });
        
        // Update label visibility based on zoom level - KEEP CONSISTENT SIZE
        // Show more labels at higher zoom levels but don't scale font size
        const labelVisibilityThreshold = Math.max(0.3, 1 / zoomScale);
        // Remove label size scaling - keep original size
        const labelSizeMultiplier = 1.0; // Always 1.0 to maintain consistent size
        
        const labelBgs = this.graphElements.g.selectAll('.label-bg');
        
        labels.each(function(d, i) {
            const label = d3.select(this);
            // Use improved font sizing consistent with main rendering - NO SCALING
            const baseSize = d.isAIGenerated ? 12 : 11;
            const sizeBonus = Math.min(4, (d.calculatedSize - 8) * 0.2);
            const originalFontSize = Math.max(9, Math.min(14, baseSize + sizeBonus));
            // Keep original font size - no scaling with zoom
            const adjustedFontSize = originalFontSize; // No multiplication by labelSizeMultiplier
            const shouldShow = (d.showText !== false) && ((d.importance || 0.5) > labelVisibilityThreshold || zoomScale > 1.2);
            
            label
                .attr('font-size', adjustedFontSize)
                .style('opacity', shouldShow ? 1 : 0)
                .attr('dx', (d.calculatedSize || 8) * minSizeMultiplier + 8);
            
            // Update corresponding label background
            if (shouldShow) {
                const labelBg = d3.select(labelBgs.nodes()[i]);
                if (!labelBg.empty()) {
                    labelBg.style('opacity', 1);
                    // Update background size and position
                    try {
                        const bbox = label.node().getBBox();
                        labelBg
                            .attr('x', bbox.x - 2)
                            .attr('y', bbox.y - 1)
                            .attr('width', bbox.width + 4)
                            .attr('height', bbox.height + 2);
                    } catch (e) {
                        // Fallback if getBBox fails
                        labelBg.style('opacity', 1);
                    }
                }
            } else {
                // Hide background when label is hidden
                const labelBg = d3.select(labelBgs.nodes()[i]);
                if (!labelBg.empty()) {
                    labelBg.style('opacity', 0);
                }
            }
        });
        
        // Also adjust link stroke widths for better visibility at different zoom levels
        const links = this.graphElements.g.selectAll('.links line');
        const linkWidthMultiplier = Math.max(0.5, Math.min(2, 1 / Math.pow(zoomScale, 0.5)));
        
        links.style('stroke-width', d => {
            const originalWidth = d.isHighlighted ? 1.0 : 0.5;
            return Math.max(0.2, originalWidth * linkWidthMultiplier);
        });
    }

    async reprocessGraphWithAI() {
        const aiBtn = document.getElementById('ai-reprocess-btn');
        if (!aiBtn || !this.currentGraphData) return;
        
        try {
            // Set button to processing state
            aiBtn.disabled = true;
            aiBtn.classList.add('processing');
            aiBtn.innerHTML = '<i class="fas fa-robot"></i> Processing...';
            
            // Get current analysis type and language
            const analysisType = document.getElementById('concept-analysis-type')?.value || 'bridges';
            const language = document.getElementById('concept-language')?.value || 'en';
            const enableLemmatization = document.getElementById('concept-lemmatization')?.checked ?? true;
            
            // Extract current nodes from graph
            const currentNodes = this.currentGraphData.nodes.map(node => ({
                id: node.id,
                label: node.label,
                size: node.size,
                importance: node.importance
            }));
            
            // Get current note text
            const noteText = await this.getNotesContentForConcept();
            if (!noteText) {
                return;
            }
            
            // Call AI reprocessing endpoint (AI provider config comes from user settings)
            const resp = await authFetch('/api/concept-graph/ai-reprocess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    note: noteText,
                    current_nodes: currentNodes,
                    analysis_type: analysisType,
                    language: language,
                    enable_lemmatization: enableLemmatization
                })
            });
            
            if (!resp.ok) {
                const errorData = await resp.json();
                throw new Error(errorData.error || 'AI reprocessing failed');
            }
            
            const data = await resp.json();
            
            // Update graph with AI-filtered results
            this.currentGraphData = data.graph;
            this.currentGraphInsights = data.insights;
            
            // Re-render the graph
            this.renderConceptGraph(data.graph);
            this.renderGraphInsights(data.insights);
            
            this.showNotification('Graph reprocessed with AI successfully', 'success');
            
        } catch (error) {
            console.error('AI reprocessing error:', error);
            this.showNotification(error.message || 'AI reprocessing failed', 'error');
        } finally {
            // Reset button state
            aiBtn.disabled = false;
            aiBtn.classList.remove('processing');
            aiBtn.innerHTML = '<i class="fas fa-robot"></i> Reprocess with AI';
        }
    }

    filterNodesUpToLevel2(nodes) {
        /**
         * Filtra los nodos para proporcionar solo los más importantes (nivel 1 y 2)
         * Los nodos se clasifican por una combinación de centralidad y importancia
         */
        if (!nodes || nodes.length === 0) return [];
        
        // Calcular un puntaje combinado para cada nodo
        const nodesWithScore = nodes.map(node => {
            const importance = node.importance || 0;
            const degreeCentrality = node.degree_centrality || 0;
            const betweennessCentrality = node.betweenness_centrality || 0;
            const nodeSize = node.size || 1;
            
            // Puntaje combinado: importancia (40%) + degree centrality (30%) + betweenness centrality (20%) + tamaño normalizado (10%)
            const combinedScore = (importance * 0.4) + (degreeCentrality * 0.3) + (betweennessCentrality * 0.2) + ((nodeSize - 1) / 20 * 0.1);
            
            return {
                ...node,
                combinedScore: combinedScore
            };
        });
        
        // Ordenar por puntaje combinado (mayor a menor)
        nodesWithScore.sort((a, b) => b.combinedScore - a.combinedScore);
        
        // Determinar cuántos nodos incluir (hasta nivel 2)
        // Nivel 1: Top 20% de los nodos (o mínimo 5, máximo 15)
        // Nivel 2: Siguiente 30% de los nodos (o mínimo 10, máximo 25)
        const totalNodes = nodes.length;
        const level1Count = Math.min(Math.max(Math.ceil(totalNodes * 0.2), 5), 15);
        const level2Count = Math.min(Math.max(Math.ceil(totalNodes * 0.3), 10), 25);
        const maxNodesForAI = Math.min(level1Count + level2Count, 40); // Límite máximo de 40 nodos
        
        // Tomar solo los nodos hasta el nivel 2
        const filteredNodes = nodesWithScore.slice(0, maxNodesForAI);
        
        console.log(`Filtered nodes for AI: ${filteredNodes.length} out of ${totalNodes} total nodes`);
        console.log(`Level 1 nodes: ${level1Count}, Level 2 nodes: ${Math.min(level2Count, maxNodesForAI - level1Count)}`);
        
        return filteredNodes;
    }

    async generateAINodes() {
        const aiBtn = document.getElementById('ai-generate-nodes-btn');
        if (!aiBtn || !this.currentGraphData) return;
        
        try {
            // Set button to processing state
            aiBtn.disabled = true;
            aiBtn.classList.add('processing');
            aiBtn.innerHTML = '<i class="fas fa-magic fa-spin"></i> Generating...';
            
            // Get current language from dropdown
            const language = document.getElementById('concept-language')?.value || 'en';
            
            // Filter nodes to only include level 1 and 2 (most important nodes)
            const filteredNodes = this.filterNodesUpToLevel2(this.currentGraphData.nodes);
            
            // Extract filtered nodes for AI
            const currentNodes = filteredNodes.map(node => ({
                id: node.id,
                label: node.label,
                size: node.size,
                importance: node.importance,
                degree_centrality: node.degree_centrality,
                betweenness_centrality: node.betweenness_centrality
            }));
            
            // Get current note text
            const noteText = await this.getNotesContentForConcept();
            if (!noteText) {
                return;
            }
            
            // Show notification about filtering
            const totalNodes = this.currentGraphData.nodes.length;
            this.showNotification(`Sending ${filteredNodes.length} of ${totalNodes} most important nodes to AI for analysis`, 'info');
            
            // Call AI node generation endpoint
            const resp = await authFetch('/api/concept-graph/ai-generate-nodes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    note: noteText,
                    current_nodes: currentNodes,
                    language: language
                })
            });
            
            if (!resp.ok) {
                const errorData = await resp.json();
                throw new Error(errorData.error || 'AI node generation failed');
            }
            
            const data = await resp.json();
            
            if (data.ai_nodes && data.ai_nodes.length > 0) {
                // Add AI nodes to current graph
                this.addAINodesToConcept(data.ai_nodes);
                this.showNotification(`Generated ${data.ai_nodes.length} AI nodes successfully`, 'success');
            } else {
                this.showNotification('No AI nodes were generated', 'info');
            }
            
        } catch (error) {
            console.error('AI node generation error:', error);
            this.showNotification(error.message || 'AI node generation failed', 'error');
        } finally {
            // Reset button state
            aiBtn.disabled = false;
            aiBtn.classList.remove('processing');
            aiBtn.innerHTML = '<i class="fas fa-magic"></i> Generate AI Organizers';
        }
    }

    addAINodesToConcept(aiNodes) {
        if (!this.currentGraphData || !aiNodes || aiNodes.length === 0) return;
        
        // Create maps for efficient node lookup by ID and label
        const existingNodeIds = new Set(this.currentGraphData.nodes.map(n => n.id));
        const labelToIdMap = new Map();
        this.currentGraphData.nodes.forEach(node => {
            labelToIdMap.set(node.label, node.id);
            labelToIdMap.set(node.id, node.id); // Also map ID to ID for direct matches
        });
        
        const newNodes = [];
        const newEdges = [];
        
        aiNodes.forEach((aiNode, index) => {
            const nodeId = `ai_${Date.now()}_${index}`;
            
            // Create AI node with special styling and high importance
            const newNode = {
                id: nodeId,
                label: aiNode.label,
                size: Math.max(18, Math.min(30, aiNode.importance * 25)), // Larger size for AI nodes
                importance: aiNode.importance,
                isAIGenerated: true, // Special flag for styling
                group: 'ai_generated',
                // Ensure AI nodes have high centrality metrics for positioning
                degree_centrality: 0.8,
                betweenness_centrality: 0.7
            };
            
            newNodes.push(newNode);
            
            // Create edges to related nodes - match by both ID and label
            if (aiNode.related_nodes && Array.isArray(aiNode.related_nodes)) {
                const connectedTargets = new Set(); // Prevent duplicate connections
                
                aiNode.related_nodes.forEach(relatedNodeRef => {
                    const relatedNodeRefStr = String(relatedNodeRef).trim();
                    
                    // Try to find the target node ID
                    let targetNodeId = null;
                    
                    // First, try direct ID match
                    if (existingNodeIds.has(relatedNodeRefStr)) {
                        targetNodeId = relatedNodeRefStr;
                    }
                    // Then, try label match
                    else if (labelToIdMap.has(relatedNodeRefStr)) {
                        targetNodeId = labelToIdMap.get(relatedNodeRefStr);
                    }
                    
                    // Create connection if target found and not already connected
                    if (targetNodeId && !connectedTargets.has(targetNodeId)) {
                        connectedTargets.add(targetNodeId);
                        newEdges.push({
                            source: nodeId,
                            target: targetNodeId,
                            strength: 0.9, // AI connections have very high strength
                            weight: 3, // High weight for important connections
                            isAIGenerated: true
                        });
                    }
                });
            }
        });
        
        // Update graph data
        this.currentGraphData.nodes = [...this.currentGraphData.nodes, ...newNodes];
        this.currentGraphData.links = [...this.currentGraphData.links, ...newEdges];
        
        console.log(`Added ${newNodes.length} AI nodes and ${newEdges.length} AI connections to the graph`);
        
        // Re-render the graph with AI nodes
        this.renderConceptGraph(this.currentGraphData);
    }

    setupAISuggestionsWindow() {
        this.currentSuggestions = [];
        this.currentSuggestionIndex = 0;
        this.suggestionTypes = ['bridge_concepts', 'knowledge_gaps', 'exploration_areas'];
        this.currentSuggestionType = 0;
        this.suggestionsWindow = document.getElementById('ai-suggestions-window');
        
        // Window controls
        const closeBtn = document.getElementById('close-suggestions');
        const minimizeBtn = document.getElementById('minimize-suggestions');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideAISuggestionsWindow();
            });
        }
        
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', () => {
                this.toggleMinimizeSuggestions();
            });
        }
        
        // Navigation controls
        const prevBtn = document.getElementById('prev-suggestion');
        const nextBtn = document.getElementById('next-suggestion');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                this.navigateSuggestion('prev');
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.navigateSuggestion('next');
            });
        }
        
        // Custom question input
        const askBtn = document.getElementById('ask-suggestion');
        const questionInput = document.getElementById('suggestion-question');
        
        if (askBtn) {
            askBtn.addEventListener('click', () => {
                this.askCustomSuggestion();
            });
        }
        
        if (questionInput) {
            questionInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.askCustomSuggestion();
                }
            });
        }
        
        // Make window draggable
        this.makeWindowDraggable();
    }

    setupConceptRemovalModal() {
        // Modal elements
        this.conceptRemovalModal = document.getElementById('concept-removal-modal');
        this.conceptExclusionsInput = document.getElementById('concept-exclusions-input');
        this.conceptInclusionsInput = document.getElementById('concept-inclusions-input');
        this.exclusionCountElement = document.getElementById('exclusion-count');
        this.inclusionCountElement = document.getElementById('inclusion-count');
        this.conceptExclusionLoading = document.getElementById('concept-exclusion-loading');
        
        // Button handlers
        const cancelBtn = document.getElementById('cancel-concept-removal');
        const saveBtn = document.getElementById('save-concept-exclusions');
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.hideConceptRemovalModal();
            });
        }
        
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveConceptFilters();
            });
        }
        
        // Input handlers to update counts
        if (this.conceptExclusionsInput) {
            this.conceptExclusionsInput.addEventListener('input', () => {
                this.updateExclusionCount();
            });
        }
        
        if (this.conceptInclusionsInput) {
            this.conceptInclusionsInput.addEventListener('input', () => {
                this.updateInclusionCount();
            });
        }
        
        // Close modal when clicking outside
        if (this.conceptRemovalModal) {
            this.conceptRemovalModal.addEventListener('click', (e) => {
                if (e.target === this.conceptRemovalModal) {
                    this.hideConceptRemovalModal();
                }
            });
        }
    }

    async showConceptRemovalModal() {
        if (!this.conceptRemovalModal) return;
        
        // Show modal
        this.conceptRemovalModal.classList.add('active');
        
        // Load current exclusions and inclusions
        await this.loadConceptExclusions();
        await this.loadConceptInclusions();
        
        // Update counts
        this.updateExclusionCount();
        this.updateInclusionCount();
        
        // Focus first input
        if (this.conceptExclusionsInput) {
            setTimeout(() => this.conceptExclusionsInput.focus(), 100);
        }
    }

    hideConceptRemovalModal() {
        if (this.conceptRemovalModal) {
            this.conceptRemovalModal.classList.remove('active');
        }
    }

    async loadConceptExclusions() {
        try {
            const response = await authFetch('/api/concept-exclusions', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (this.conceptExclusionsInput) {
                    this.conceptExclusionsInput.value = data.exclusions.join(', ');
                }
            } else {
                console.warn('Failed to load concept exclusions');
                if (this.conceptExclusionsInput) {
                    this.conceptExclusionsInput.value = '';
                }
            }
        } catch (error) {
            console.error('Error loading concept exclusions:', error);
            if (this.conceptExclusionsInput) {
                this.conceptExclusionsInput.value = '';
            }
        }
    }

    async saveConceptFilters() {
        if (!this.conceptExclusionsInput || !this.conceptInclusionsInput) return;
        
        const exclusionsInput = this.conceptExclusionsInput.value.trim();
        const exclusions = exclusionsInput ? exclusionsInput.split(',').map(word => word.trim()).filter(word => word) : [];
        
        const inclusionsInput = this.conceptInclusionsInput.value.trim();
        const inclusions = inclusionsInput ? inclusionsInput.split(',').map(word => word.trim()).filter(word => word) : [];
        
        // Show loading
        if (this.conceptExclusionLoading) {
            this.conceptExclusionLoading.classList.remove('hidden');
        }
        
        try {
            // Save exclusions
            const exclusionsResponse = await authFetch('/api/concept-exclusions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ exclusions })
            });
            
            // Save inclusions
            const inclusionsResponse = await authFetch('/api/concept-inclusions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ inclusions })
            });
            
            if (exclusionsResponse.ok && inclusionsResponse.ok) {
                const exclusionsData = await exclusionsResponse.json();
                const inclusionsData = await inclusionsResponse.json();
                this.showNotification(`Saved ${exclusionsData.exclusions.length} exclusions and ${inclusionsData.inclusions.length} inclusions`, 'success');
                this.hideConceptRemovalModal();
            } else {
                throw new Error('Failed to save filters');
            }
        } catch (error) {
            console.error('Error saving concept filters:', error);
            this.showNotification(error.message || 'Failed to save concept filters', 'error');
        } finally {
            // Hide loading
            if (this.conceptExclusionLoading) {
                this.conceptExclusionLoading.classList.add('hidden');
            }
        }
    }

    async loadConceptInclusions() {
        try {
            const response = await authFetch('/api/concept-inclusions', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (this.conceptInclusionsInput) {
                    this.conceptInclusionsInput.value = data.inclusions.join(', ');
                }
            } else {
                console.warn('Failed to load concept inclusions');
                if (this.conceptInclusionsInput) {
                    this.conceptInclusionsInput.value = '';
                }
            }
        } catch (error) {
            console.error('Error loading concept inclusions:', error);
            if (this.conceptInclusionsInput) {
                this.conceptInclusionsInput.value = '';
            }
        }
    }

    updateExclusionCount() {
        if (!this.conceptExclusionsInput || !this.exclusionCountElement) return;
        
        const input = this.conceptExclusionsInput.value.trim();
        const count = input ? input.split(',').map(word => word.trim()).filter(word => word).length : 0;
        
        this.exclusionCountElement.textContent = count;
    }

    updateInclusionCount() {
        if (!this.conceptInclusionsInput || !this.inclusionCountElement) return;
        
        const input = this.conceptInclusionsInput.value.trim();
        const count = input ? input.split(',').map(word => word.trim()).filter(word => word).length : 0;
        
        this.inclusionCountElement.textContent = count;
    }

    async showAISuggestionsWindow() {
        if (!this.currentGraphData) return;
        
        this.suggestionsWindow.classList.remove('hidden');
        this.suggestionsWindow.classList.remove('minimized');
        
        // Reset suggestion tracking
        this.currentSuggestions = [];
        this.currentSuggestionIndex = 0;
        this.currentSuggestionType = 0;
        
        // Generate the first suggestion
        await this.generateNextSuggestion();
    }

    hideAISuggestionsWindow() {
        this.suggestionsWindow.classList.add('hidden');
    }

    toggleMinimizeSuggestions() {
        this.suggestionsWindow.classList.toggle('minimized');
    }

    navigateSuggestion(direction) {
        if (direction === 'prev') {
            if (this.currentSuggestionIndex > 0) {
                this.currentSuggestionIndex--;
                this.displayCurrentSuggestion();
            }
        } else if (direction === 'next') {
            // If we have more cached suggestions, show them
            if (this.currentSuggestionIndex < this.currentSuggestions.length - 1) {
                this.currentSuggestionIndex++;
                this.displayCurrentSuggestion();
            } else {
                // Generate next suggestion
                this.generateNextSuggestion();
            }
        }
    }

    async generateNextSuggestion() {
        const content = document.getElementById('suggestion-content');
        
        // Show loading state
        content.innerHTML = `
            <div class="suggestion-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Generating AI suggestion...</span>
            </div>
        `;
        
        try {
            // Get current note text and nodes
            const noteText = await this.getNotesContentForConcept();
            if (!noteText) {
                content.innerHTML = '<p>Error: Could not get note content</p>';
                return;
            }
            
            const analysisType = document.getElementById('concept-analysis-type')?.value || 'bridges';
            const language = document.getElementById('concept-language')?.value || 'en';
            const enableLemmatization = document.getElementById('concept-lemmatization')?.checked ?? true;
            
            // Extract current nodes from graph
            const currentNodes = this.currentGraphData.nodes.map(node => ({
                id: node.id,
                label: node.label,
                size: node.size,
                importance: node.importance
            }));
            
            // Get the suggestion type to generate
            const suggestionType = this.suggestionTypes[this.currentSuggestionType % this.suggestionTypes.length];
            
            // Call single suggestion endpoint
            const resp = await authFetch('/api/concept-graph/ai-single-suggestion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    note: noteText,
                    current_nodes: currentNodes,
                    suggestion_type: suggestionType,
                    analysis_type: analysisType,
                    language: language,
                    enable_lemmatization: enableLemmatization
                })
            });
            
            if (!resp.ok) {
                const errorData = await resp.json();
                throw new Error(errorData.error || 'Failed to generate suggestion');
            }
            
            const data = await resp.json();
            const newSuggestion = data.suggestion;
            
            if (newSuggestion) {
                // Add to suggestions array
                this.currentSuggestions.push(newSuggestion);
                this.currentSuggestionIndex = this.currentSuggestions.length - 1;
                this.currentSuggestionType++;
                
                // Process thinking tags and display
                await this.displaySuggestionWithStreaming(newSuggestion);
            } else {
                content.innerHTML = '<p>No suggestion available. Try regenerating the concept graph first.</p>';
            }
            
        } catch (error) {
            console.error('Error generating AI suggestion:', error);
            content.innerHTML = `<p>Error generating suggestion: ${error.message}</p>`;
        }
    }

    displayCurrentSuggestion() {
        if (this.currentSuggestions.length === 0) return;
        
        const suggestion = this.currentSuggestions[this.currentSuggestionIndex];
        const content = document.getElementById('suggestion-content');
        const counter = document.getElementById('suggestion-counter');
        
        // Update counter
        counter.textContent = `${this.currentSuggestionIndex + 1} / ${this.currentSuggestions.length}`;
        
        // Update navigation buttons
        const prevBtn = document.getElementById('prev-suggestion');
        const nextBtn = document.getElementById('next-suggestion');
        
        if (prevBtn) prevBtn.disabled = this.currentSuggestionIndex === 0;
        if (nextBtn) nextBtn.disabled = false; // Next is always enabled for new generation
        
        // Display suggestion content with highlighted concepts
        const highlightedContent = this.highlightConceptsInText(suggestion.content, suggestion.concepts || []);
        
        content.innerHTML = `
            <div class="suggestion-item">
                <h4 class="suggestion-title">${suggestion.title}</h4>
                <div class="suggestion-text">${highlightedContent}</div>
            </div>
        `;
    }

    async displaySuggestionWithStreaming(suggestion) {
        const content = document.getElementById('suggestion-content');
        const counter = document.getElementById('suggestion-counter');
        
        // Update counter
        counter.textContent = `${this.currentSuggestionIndex + 1} / ${this.currentSuggestions.length}`;
        
        // Update navigation buttons
        const prevBtn = document.getElementById('prev-suggestion');
        const nextBtn = document.getElementById('next-suggestion');
        
        if (prevBtn) prevBtn.disabled = this.currentSuggestionIndex === 0;
        if (nextBtn) nextBtn.disabled = false;
        
        // Check for thinking tags
        const thinkingResult = this.processThinkTags(suggestion.content);
        
        if (thinkingResult.hasThinking) {
            // Show thinking phase
            content.innerHTML = `
                <div class="suggestion-item">
                    <h4 class="suggestion-title">${suggestion.title}</h4>
                    <div class="thinking-indicator">
                        <i class="fas fa-brain fa-pulse"></i>
                        <span>Thinking...</span>
                    </div>
                </div>
            `;
            
            // Wait a moment to show thinking
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // Display the response with streaming effect
        content.innerHTML = `
            <div class="suggestion-item">
                <h4 class="suggestion-title">${suggestion.title}</h4>
                <div class="suggestion-text" id="streaming-suggestion"></div>
            </div>
        `;
        
        const streamingElement = document.getElementById('streaming-suggestion');
        const textToDisplay = thinkingResult.hasThinking ? thinkingResult.response : suggestion.content;
        
        // Simulate streaming
        await this.streamText(streamingElement, textToDisplay, suggestion.concepts || []);
    }

    processThinkTags(text) {
        // Check for thinking tags
        const thinkPattern = /<think>(.*?)<\/think>/gis;
        const thinkingMatches = text.match(thinkPattern);
        
        if (thinkingMatches) {
            // Remove thinking sections from response
            const responseText = text.replace(thinkPattern, '').trim();
            return {
                hasThinking: true,
                thinking: thinkingMatches.join('\n'),
                response: responseText
            };
        }
        
        return {
            hasThinking: false,
            thinking: '',
            response: text
        };
    }

    async streamText(element, text, concepts) {
        element.innerHTML = '';
        
        for (let i = 0; i <= text.length; i++) {
            const partialText = text.substring(0, i);
            const highlightedText = this.highlightConceptsInText(partialText, concepts);
            element.innerHTML = highlightedText;
            
            // Add streaming cursor
            if (i < text.length) {
                element.innerHTML += '<span class="suggestion-streaming">|</span>';
                await new Promise(resolve => setTimeout(resolve, 20));
            }
        }
    }

    highlightConceptsInText(text, concepts) {
        if (!concepts || concepts.length === 0) return text;
        
        let highlightedText = text;
        
        // Get node colors from current graph
        const nodeColorMap = {};
        if (this.currentGraphData && this.currentGraphData.nodes) {
            this.currentGraphData.nodes.forEach(node => {
                nodeColorMap[node.label.toLowerCase()] = node.color || '#3b82f6';
            });
        }
        
        // Highlight each concept with its graph color
        concepts.forEach(concept => {
            const color = nodeColorMap[concept.toLowerCase()] || '#8b5cf6';
            const regex = new RegExp(`\\b${concept.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            highlightedText = highlightedText.replace(regex, 
                `<span class="suggestion-concept" style="background-color: ${color}; color: white;">${concept}</span>`
            );
        });
        
        return highlightedText;
    }

    async askCustomSuggestion() {
        const questionInput = document.getElementById('suggestion-question');
        const question = questionInput.value.trim();
        
        if (!question) return;
        
        const content = document.getElementById('suggestion-content');
        
        // Show loading state
        content.innerHTML = `
            <div class="suggestion-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Getting AI response...</span>
            </div>
        `;
        
        try {
            // Get current note text and nodes
            const noteText = await this.getNotesContentForConcept();
            if (!noteText) {
                content.innerHTML = '<p>Error: Could not get note content</p>';
                return;
            }
            
            const language = document.getElementById('concept-language')?.value || 'en';
            
            // Extract current nodes from graph
            const currentNodes = this.currentGraphData.nodes.map(node => ({
                id: node.id,
                label: node.label,
                size: node.size,
                importance: node.importance
            }));
            
            // Set up streaming display
            content.innerHTML = `
                <div class="suggestion-item">
                    <h4 class="suggestion-title">Custom Question</h4>
                    <p class="suggestion-question"><strong>Q:</strong> ${question}</p>
                    <div class="suggestion-text suggestion-streaming" id="streaming-text"></div>
                </div>
            `;
            
            const streamingElement = document.getElementById('streaming-text');
            
            // Call streaming endpoint
            const resp = await authFetch('/api/concept-graph/ai-custom-suggestion-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    note: noteText,
                    current_nodes: currentNodes,
                    language: language
                })
            });
            
            if (!resp.ok) {
                const errorData = await resp.json();
                throw new Error(errorData.error || 'Failed to get custom suggestion');
            }
            
            // Process streaming response
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';
            let isThinking = false;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            // Streaming complete - process final think tags
                            const thinkingResult = this.processThinkTags(fullResponse);
                            if (thinkingResult.hasThinking) {
                                const highlightedText = this.highlightConceptsInText(
                                    thinkingResult.response, 
                                    this.extractConceptsFromCurrentGraph()
                                );
                                streamingElement.innerHTML = highlightedText;
                            }
                            streamingElement.classList.remove('suggestion-streaming');
                            // Clear input
                            questionInput.value = '';
                            return;
                        }
                        
                        try {
                            const parsed = JSON.parse(data);
                            const content = parsed.choices?.[0]?.delta?.content || '';
                            if (content) {
                                fullResponse += content;
                                
                                // Check for think tags in current response
                                const hasThinkStart = fullResponse.includes('<think>');
                                const hasThinkEnd = fullResponse.includes('</think>');
                                
                                if (hasThinkStart && !hasThinkEnd) {
                                    // Currently in thinking mode
                                    if (!isThinking) {
                                        isThinking = true;
                                        streamingElement.innerHTML = `
                                            <div class="thinking-indicator">
                                                <i class="fas fa-brain fa-pulse"></i>
                                                <span>Thinking...</span>
                                            </div>
                                        `;
                                    }
                                } else if (hasThinkEnd && isThinking) {
                                    // Thinking completed
                                    isThinking = false;
                                    const thinkingResult = this.processThinkTags(fullResponse);
                                    const highlightedText = this.highlightConceptsInText(
                                        thinkingResult.response, 
                                        this.extractConceptsFromCurrentGraph()
                                    );
                                    streamingElement.innerHTML = highlightedText;
                                } else if (!isThinking) {
                                    // Normal streaming without thinking
                                    const highlightedText = this.highlightConceptsInText(
                                        fullResponse, 
                                        this.extractConceptsFromCurrentGraph()
                                    );
                                    streamingElement.innerHTML = highlightedText;
                                }
                            }
                        } catch (e) {
                            // Skip invalid JSON
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Error getting custom suggestion:', error);
            
            // Show error message
            content.innerHTML = `
                <div class="suggestion-item">
                    <h4 class="suggestion-title">Error</h4>
                    <div class="suggestion-text" style="color: #ef4444;">
                        ${error.message}
                    </div>
                </div>
            `;
            
            setTimeout(() => {
                // Reset to previous content after error
                if (this.currentSuggestions.length > 0) {
                    this.displayCurrentSuggestion();
                }
            }, 3000);
        }
    }

    extractConceptsFromCurrentGraph() {
        if (!this.currentGraphData || !this.currentGraphData.nodes) return [];
        return this.currentGraphData.nodes.map(node => node.label);
    }

    makeWindowDraggable() {
        const header = document.querySelector('.ai-suggestions-header');
        if (!header) return;
        
        let isDragging = false;
        let currentX = 0;
        let currentY = 0;
        let initialX = 0;
        let initialY = 0;
        let xOffset = 0;
        let yOffset = 0;
        
        header.addEventListener('mousedown', (e) => {
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
            
            if (e.target === header || header.contains(e.target)) {
                isDragging = true;
                header.style.cursor = 'grabbing';
            }
        });
        
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                e.preventDefault();
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                
                xOffset = currentX;
                yOffset = currentY;
                
                this.suggestionsWindow.style.transform = `translate(${currentX}px, ${currentY}px)`;
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                initialX = currentX;
                initialY = currentY;
                isDragging = false;
                header.style.cursor = 'move';
            }
        });
        
        header.style.cursor = 'move';
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

    setupPdfUploadDropZone() {
        const dropZone = document.getElementById('pdf-drop-zone');
        const fileInput = document.getElementById('pdf-file-input');
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
            const files = Array.from(e.dataTransfer.files);
            this.handlePdfFileSelection(files);
        });
        
        if (fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', e => {
                const files = Array.from(e.target.files);
                this.handlePdfFileSelection(files);
                fileInput.value = '';
            });
        }
    }

    handlePdfFileSelection(files) {
        if (!files.length) return;
        
        // Filter only PDF and TXT files
        const validFiles = files.filter(f => {
            const ext = f.name.toLowerCase().split('.').pop();
            return ext === 'pdf' || ext === 'txt';
        });
        
        if (validFiles.length === 0) {
            this.showNotification('Please select only PDF or TXT files', 'error');
            return;
        }
        
        if (validFiles.length > 1) {
            this.showNotification('Please select only one file at a time', 'error');
            return;
        }
        
        // Store the selected file and enable upload button
        this.selectedPdfFile = validFiles[0];
        const confirmBtn = document.getElementById('confirm-upload-pdf');
        confirmBtn.disabled = false;
        
        // Update drop zone to show selected file
        const dropZone = document.getElementById('pdf-drop-zone');
        dropZone.innerHTML = `
            <i class="fas fa-file-${validFiles[0].name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'alt'}"></i>
            <p><strong>${validFiles[0].name}</strong></p>
            <p>Ready to upload (${this.formatFileSize(validFiles[0].size)})</p>
        `;
        
        this.showNotification(`Selected: ${validFiles[0].name}`, 'success');
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
        
        // Gather tags from notes array
        this.notes.forEach(n => (n.tags || []).forEach(t => set.add(t)));
        
        // If in folder view, also gather tags from folder structure
        if (this.currentViewMode === 'folder' && this.folderStructure) {
            this.gatherTagsFromFolderStructure(this.folderStructure, set);
        }
        
        return Array.from(set).sort();
    }
    
    gatherTagsFromFolderStructure(items, set) {
        items.forEach(item => {
            if (item.type === 'folder' && item.children) {
                this.gatherTagsFromFolderStructure(item.children, set);
            } else if (item.type === 'note' && item.tags) {
                item.tags.forEach(tag => set.add(tag));
            }
        });
    }
    
    // Update note title in local folder structure
    updateNoteInFolderStructure(noteId, newTitle) {
        const updateInItems = (items) => {
            items.forEach(item => {
                if (item.type === 'folder' && item.children) {
                    updateInItems(item.children);
                } else if (item.type === 'note' && item.id === noteId) {
                    item.name = newTitle;
                }
            });
        };
        
        if (this.folderStructure && this.folderStructure.length > 0) {
            updateInItems(this.folderStructure);
        }
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
                // Refresh current view based on view mode
                this.refreshCurrentView();
            });
        });
        container.style.display = tags.length ? 'flex' : 'none';
        
        // Update concept tag filter if visible
        const conceptTagContainer = document.getElementById('tag-selection-container');
        if (conceptTagContainer && !conceptTagContainer.classList.contains('hidden')) {
            this.renderConceptTagFilter();
        }
    }

    renderNoteTags(note) {
        const container = document.getElementById('note-tags');
        if (!container) return;
        const tags = (note && note.tags) ? note.tags : [];
        
        // Create the main tag container structure
        const tagStructure = `
            <div class="current-tags">
                ${tags.map(t => `<span class="tag-badge" data-tag="${t}">${t}<span class="remove-tag" data-tag="${t}">&times;</span></span>`).join('')}
            </div>
            <div class="available-tags-section">
                <div class="available-tags-container">
                    <div class="available-tags-scroll" id="available-tags-scroll"></div>
                </div>
            </div>
        `;
        
        safeSetInnerHTML(container, tagStructure);
        
        // Add the input field
        const currentTagsContainer = container.querySelector('.current-tags');
        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'tag-input';
        input.className = 'tag-input';
        input.placeholder = 'Add tag...';
        currentTagsContainer.appendChild(input);

        // Render available tags
        this.renderAvailableTags();

        // Add event listeners for removing tags
        container.querySelectorAll('.remove-tag').forEach(btn => {
            const tag = btn.dataset.tag;
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeTag(tag);
            });
        });

        // Add event listeners for input
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

    renderAvailableTags() {
        const container = document.getElementById('available-tags-scroll');
        if (!container) return;
        
        const allTags = this.gatherAllTags();
        const currentTags = (this.currentNote && this.currentNote.tags) ? this.currentNote.tags : [];
        const availableTags = allTags.filter(tag => !currentTags.includes(tag));
        
        if (availableTags.length === 0) {
            container.innerHTML = '';
            return;
        }
        
        container.innerHTML = availableTags.map(tag => 
            `<span class="available-tag-badge" data-tag="${tag}" title="Click to add tag">${tag}</span>`
        ).join('');
        
        // Add click listeners to available tags
        container.querySelectorAll('.available-tag-badge').forEach(badge => {
            badge.addEventListener('click', () => {
                const tag = badge.dataset.tag;
                this.addTag(tag);
            });
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
        
        // Only render list view if we're in list mode
        if (this.currentViewMode !== 'list') {
            return;
        }
        
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
                    <h3>No notes yet</h3>
                    <p>Create your first note to get started</p>
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
                    <div class="note-item-content">
                        <div class="note-item-title">${note.title}</div>
                        <div class="note-item-preview">${preview}</div>
                        <div class="note-item-date">${date}</div>
                    </div>
                    <div class="note-item-actions">
                        <button class="note-delete-btn" data-note-id="${note.id}" title="Delete note">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join(''));
        
        // Agregar event listeners a los items
        container.querySelectorAll('.note-item').forEach(item => {
            // Click event for the note content (not the delete button)
            const noteContent = item.querySelector('.note-item-content');
            if (noteContent) {
                noteContent.addEventListener('click', async () => {
                    const noteId = parseInt(item.dataset.noteId);
                    await this.selectNote(noteId);
                });
            }
        });

        // Add event listeners for delete buttons
        container.querySelectorAll('.note-delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const noteId = parseInt(btn.dataset.noteId);
                this.showDeleteNoteModal(noteId);
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
        let stream;
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

            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
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
           const chunkDuration = parseInt(this.config.chunkDuration || 0);
           const useChunkStreaming = chunkDuration > 0 && (
               (this.config.transcriptionProvider === 'local' && this.config.localEnableStreaming) ||
               (this.config.transcriptionProvider === 'sensevoice' && this.config.sensevoiceEnableStreaming)
           );

           this.recordingStream = stream;
           this.useChunkStreaming = useChunkStreaming;
           this.chunkDuration = chunkDuration;

           if (useChunkStreaming) {
               this.setEditorReadOnly(true);
           }

            this.chunkQueue = [];
            this.processingChunk = false;

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    if (useChunkStreaming) {
                        this.chunkQueue.push(event.data);
                        if (!this.processingChunk) {
                            this.processNextChunk();
                        }
                    }
                }
            };

           this.mediaRecorder.onstop = async () => {
               if (useChunkStreaming && this.isRecording) {
                   // restart recording for next chunk
                   this.mediaRecorder.start();
                   this.chunkTimeout = setTimeout(() => {
                       if (this.mediaRecorder.state === 'recording') {
                           this.mediaRecorder.stop();
                       }
                   }, this.chunkDuration * 1000);
                   return;
               }

               const audioBlob = new Blob(this.audioChunks, { type: mimeType });
               if (useChunkStreaming) {
                   await this.waitForChunkQueue();
               } else {
                   await this.transcribeAudio(audioBlob);
               }
               await this.saveRecordedAudio(audioBlob);

               if (useChunkStreaming) {
                   this.setEditorReadOnly(false);
               }

               // Stop stream
               stream.getTracks().forEach(track => track.stop());
           };

            if (useChunkStreaming) {
                this.mediaRecorder.start();
                this.chunkTimeout = setTimeout(() => {
                    if (this.mediaRecorder.state === 'recording') {
                        this.mediaRecorder.stop();
                    }
                }, this.chunkDuration * 1000);
            } else {
                this.mediaRecorder.start();
            }
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
            if (this.chunkTimeout) {
                clearTimeout(this.chunkTimeout);
                this.chunkTimeout = null;
            }
            this.isRecording = false;
            if (this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.stop();
            }
            
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
            
            const enableSpeakerDiarization = this.config.localEnableSpeakerDiarization || false;
            
            const result = await backendAPI.transcribeAudio(
                audioBlob,
                this.config.transcriptionLanguage,
                this.config.transcriptionModel,
                'local',
                enableSpeakerDiarization
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
            const enableSpeakerDiarization = document.getElementById('enable-speaker-diarization')?.checked ?? false;
            
            const result = await backendAPI.transcribeAudioSenseVoice(
                audioBlob,
                this.config.transcriptionLanguage,
                detectEmotion,
                detectEvents,
                useItn,
                enableSpeakerDiarization
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
        
        // Convert newlines to HTML breaks for proper rendering
        // This ensures speaker diarization line breaks are visible immediately
        const formattedText = transcription.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
        
        // Create a temporary container to convert HTML to DOM nodes
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = formattedText;
        
        // Insert each node from the temporary container
        while (tempDiv.firstChild) {
            const node = tempDiv.removeChild(tempDiv.firstChild);
            range.insertNode(node);
            range.setStartAfter(node);
            range.setEndAfter(node);
        }
        
        // Add a space after the transcription
        const spaceNode = document.createTextNode(' ');
        range.insertNode(spaceNode);
        range.setStartAfter(spaceNode);
        range.setEndAfter(spaceNode);
        
        selection.removeAllRanges();
        selection.addRange(range);
        this.insertionRange = range.cloneRange();

        // Remove insertion marker after inserting text
        const marker = document.getElementById('insertion-marker');
        if (marker) marker.remove();

        // Disparar evento de cambio
        this.handleEditorChange();
        
        console.log('Transcription inserted successfully with proper line breaks');
    }

    async uploadAudioFile(file, skipSave = false) {
        if (!this.currentNote) {
            this.showNotification('Please select a note first', 'error');
            return;
        }
        const chunkDuration = parseInt(this.config.chunkDuration || 0);
        const useChunkStreaming = chunkDuration > 0 && (
            (this.config.transcriptionProvider === 'local' && this.config.localEnableStreaming) ||
            (this.config.transcriptionProvider === 'sensevoice' && this.config.sensevoiceEnableStreaming)
        );

        if (!useChunkStreaming) {
            this.showProcessingOverlay(skipSave ? 'Processing audio...' : 'Uploading audio...');
        } else {
            this.setEditorReadOnly(true);
        }
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
            
            // Speaker diarization settings
            if (this.config.transcriptionProvider === 'sensevoice') {
                formData.append('enable_speaker_diarization', document.getElementById('enable-speaker-diarization')?.checked ?? false);
            } else if (this.config.transcriptionProvider === 'local') {
                formData.append('enable_speaker_diarization', document.getElementById('local-enable-speaker-diarization')?.checked ?? false);
            }
            
            formData.append('skip_save', skipSave ? 'true' : 'false');
            let response;
            if (useChunkStreaming) {
                formData.append('chunk_duration', chunkDuration.toString());
                response = await authFetch('/api/upload-audio-stream', { method: 'POST', body: formData });
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText);
                }
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let done = false;
                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    if (readerDone) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.slice(6));
                            if (data.transcription) {
                                this.insertTranscription(data.transcription);
                            }
                            if (data.done) {
                                done = true;
                                if (!skipSave && data.filename) {
                                    await this.loadAudioFiles(this.currentNote.id);
                                }
                            }
                        }
                    }
                }
            } else {
                response = await authFetch('/api/upload-audio', { method: 'POST', body: formData });
                const result = await response.json();
                if (response.ok) {
                    if (result.transcription) {
                        this.insertTranscription(result.transcription);
                    }
                    if (!skipSave) {
                        await this.loadAudioFiles(this.currentNote.id);
                    }
                } else {
                    this.showNotification(result.error || 'Upload failed', 'error');
                }
            }
            this.showNotification(skipSave ? 'Audio processed' : 'Audio uploaded');
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Error uploading audio', 'error');
        } finally {
            if (!useChunkStreaming) {
                this.hideProcessingOverlay();
            } else {
                this.setEditorReadOnly(false);
            }
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

    async processNextChunk() {
        if (this.chunkQueue.length === 0) {
            this.processingChunk = false;
            return;
        }
        this.processingChunk = true;
        const chunk = this.chunkQueue.shift();
        try {
            await this.transcribeChunk(chunk);
        } catch (e) {
            console.error('Chunk transcription error', e);
        }
        this.processingChunk = false;
        this.processNextChunk();
    }

    async waitForChunkQueue() {
        while (this.processingChunk || this.chunkQueue.length > 0) {
            await new Promise(r => setTimeout(r, 200));
        }
    }

    async transcribeChunk(audioBlob) {
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
            }
        } catch (error) {
            console.error('Chunk transcription error:', error);
        }
    }
    
    // Mejora con IA
    async improveText(action) {
        if (action === 'translation') {
            this.updateTranslationStyle();
        }
        if (action === 'tabularize') {
            this.updateTabularizeStyle();
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
                if (action === 'tabularize') {
                    tempSpan.innerHTML = improvedText;
                } else {
                    tempSpan.textContent = improvedText;
                }
                
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
                if (action === 'tabularize') {
                    tempSpan.innerHTML = textToImprove;
                } else {
                    tempSpan.textContent = textToImprove;
                }
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
                                let finalText = this.cleanAIResponse(state.improvedText);
                                if (action === 'diarization_fix') {
                                    finalText = this.formatDiarizationTags(finalText);
                                    tempElement.innerHTML = finalText.replace(/\n/g, '<br>');
                                } else if (action === 'tabularize') {
                                    finalText = this.convertRCToTable(finalText);
                                    tempElement.innerHTML = finalText;
                                } else {
                                    tempElement.textContent = finalText;
                                }
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
            
            let finalResult = this.cleanAIResponse(state.improvedText);
            if (action === 'diarization_fix') {
                finalResult = this.formatDiarizationTags(finalResult);
            } else if (action === 'tabularize') {
                finalResult = this.convertRCToTable(finalResult);
            }
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
                                let finalText = this.cleanAIResponse(state.improvedText);
                                if (action === 'diarization_fix') {
                                    finalText = this.formatDiarizationTags(finalText);
                                    tempElement.innerHTML = finalText.replace(/\n/g, '<br>');
                                } else if (action === 'tabularize') {
                                    finalText = this.convertRCToTable(finalText);
                                    tempElement.innerHTML = finalText;
                                } else {
                                    tempElement.textContent = finalText;
                                }
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
            
            let finalResult = this.cleanAIResponse(state.improvedText);
            if (action === 'diarization_fix') {
                finalResult = this.formatDiarizationTags(finalResult);
            } else if (action === 'tabularize') {
                finalResult = this.convertRCToTable(finalResult);
            }
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
                                let finalText = this.cleanAIResponse(state.improvedText);
                                if (action === 'diarization_fix') {
                                    finalText = this.formatDiarizationTags(finalText);
                                    tempElement.innerHTML = finalText.replace(/\n/g, '<br>');
                                } else if (action === 'tabularize') {
                                    finalText = this.convertRCToTable(finalText);
                                    tempElement.innerHTML = finalText;
                                } else {
                                    tempElement.textContent = finalText;
                                }
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
            
            let finalResult = this.cleanAIResponse(state.improvedText);
            if (action === 'diarization_fix') {
                finalResult = this.formatDiarizationTags(finalResult);
            } else if (action === 'tabularize') {
                finalResult = this.convertRCToTable(finalResult);
            }
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
                                let finalText = this.cleanAIResponse(state.improvedText);
                                if (action === 'diarization_fix') {
                                    finalText = this.formatDiarizationTags(finalText);
                                    tempElement.innerHTML = finalText.replace(/\n/g, '<br>');
                                } else if (action === 'tabularize') {
                                    finalText = this.convertRCToTable(finalText);
                                    tempElement.innerHTML = finalText;
                                } else {
                                    tempElement.textContent = finalText;
                                }
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

            let finalResult = this.cleanAIResponse(state.improvedText);
            if (action === 'diarization_fix') {
                finalResult = this.formatDiarizationTags(finalResult);
            } else if (action === 'tabularize') {
                finalResult = this.convertRCToTable(finalResult);
            }
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
                                let finalText = this.cleanAIResponse(state.improvedText);
                                if (action === 'diarization_fix') {
                                    finalText = this.formatDiarizationTags(finalText);
                                    tempElement.innerHTML = finalText.replace(/\n/g, '<br>');
                                } else if (action === 'tabularize') {
                                    finalText = this.convertRCToTable(finalText);
                                    tempElement.innerHTML = finalText;
                                } else {
                                    tempElement.textContent = finalText;
                                }
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

            let finalResult = this.cleanAIResponse(state.improvedText);
            if (action === 'diarization_fix') {
                finalResult = this.formatDiarizationTags(finalResult);
            } else if (action === 'tabularize') {
                finalResult = this.convertRCToTable(finalResult);
            }
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
                                let finalText = this.cleanAIResponse(state.improvedText);
                                if (action === 'diarization_fix') {
                                    finalText = this.formatDiarizationTags(finalText);
                                    tempElement.innerHTML = finalText.replace(/\n/g, '<br>');
                                } else if (action === 'tabularize') {
                                    finalText = this.convertRCToTable(finalText);
                                    tempElement.innerHTML = finalText;
                                } else {
                                    tempElement.textContent = finalText;
                                }
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

            let finalResult = this.cleanAIResponse(state.improvedText);
            if (action === 'diarization_fix') {
                finalResult = this.formatDiarizationTags(finalResult);
            }
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

    // Format speaker tags: place each [SPEAKER X] on a new line and remove
    // duplicate tags for the same speaker within a single line
    formatDiarizationTags(text) {
        if (!text) return '';
        let normalized = text.replace(/\[speaker\s*(\d+)\]/gi, '[SPEAKER $1]');
        const parts = normalized.split(/(\[SPEAKER\s*\d+\])/i).filter(p => p);
        let result = '';
        let current = null;
        for (const part of parts) {
            if (/^\[SPEAKER\s*\d+\]$/i.test(part)) {
                const tag = part.toUpperCase();
                if (tag !== current) {
                    if (result) result += '\n\n';
                    result += tag;
                    current = tag;
                }
            } else {
                result += ' ' + part.trim();
            }
        }
        return result.trim();
    }

    convertRCToTable(text) {
        if (!text) return '';
        const regex = /\[R(\d+)-C(\d+)\s*\/\/\s*([^\]]*)\]/g;
        const table = {};
        let maxRow = 0;
        let maxCol = 0;
        let match;
        while ((match = regex.exec(text)) !== null) {
            const r = parseInt(match[1], 10);
            const c = parseInt(match[2], 10);
            maxRow = Math.max(maxRow, r);
            maxCol = Math.max(maxCol, c);
            if (!table[r]) table[r] = {};
            table[r][c] = match[3].trim();
        }
        if (maxRow === 0 || maxCol === 0) return text;
        let html = '<table class="ai-table"><tbody>';
        for (let r = 1; r <= maxRow; r++) {
            html += '<tr>';
            for (let c = 1; c <= maxCol; c++) {
                const val = (table[r] && table[r][c]) ? table[r][c] : '';
                if (r === 1) {
                    html += `<th>${val}</th>`;
                } else {
                    html += `<td>${val}</td>`;
                }
            }
            html += '</tr>';
        }
        html += '</tbody></table>';
        return html;
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
            },
            remove_emoji: (texto) => {
                return texto.replace(/[\p{Emoji_Presentation}\p{Extended_Pictographic}]/gu, '').trim();
            },
            diarization_fix: (texto) => {
                return this.formatDiarizationTags(texto);
            },
            tabularize: (texto) => {
                return this.convertRCToTable(texto);
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

    showDeleteNoteModal(noteId) {
        this.noteToDelete = noteId;
        const modal = document.getElementById('delete-modal');
        this.hideMobileFab();
        modal.classList.add('active');
    }

    async deleteSpecificNote(noteId) {
        // Store the note to delete
        const noteToDelete = this.notes.find(note => note.id === noteId);
        if (!noteToDelete) {
            console.error('Note not found');
            return;
        }

        // Remove from notes array
        this.notes = this.notes.filter(note => note.id !== noteId);
        this.saveToStorage();

        // If this was the current note, clear it
        if (this.currentNote && this.currentNote.id === noteId) {
            this.currentNote = null;
            await this.setupDefaultNote();
        }

        // Refresh current view immediately
        if (this.currentViewMode === 'folder') {
            // Remove the note from current folder structure for immediate UI update
            this.removeNoteFromFolderStructure(noteId);
            this.renderFolderTree();
        } else {
            this.renderNotesList();
        }

        // Delete from server
        this.deleteNoteFromServer(noteId);

        this.hideDeleteModal();
        this.showNotification('Note deleted');
    }

    removeNoteFromFolderStructure(noteId) {
        // Recursively remove note from folder structure
        const removeFromItems = (items) => {
            return items.filter(item => {
                if (item.type === 'note' && item.id === noteId) {
                    return false; // Remove this note
                } else if (item.type === 'folder' && item.children) {
                    item.children = removeFromItems(item.children);
                }
                return true;
            });
        };
        
        this.folderStructure = removeFromItems(this.folderStructure);
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
        const localWhisperOptions = document.getElementById('local-whisper-options');
        
        if (sensevoiceOptions) {
            sensevoiceOptions.style.display = provider === 'sensevoice' ? 'block' : 'none';
        }
        
        if (localWhisperOptions) {
            localWhisperOptions.style.display = provider === 'local' ? 'block' : 'none';
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

    updateTabularizeStyle() {
        const style = this.stylesConfig.tabularize;
        if (!style) return;
        if (this.config.tabularizeEnabled) {
            const code = this.config.tabularizeLanguage || 'en';
            let langName = code;
            const select = document.getElementById('tabularize-language');
            if (select) {
                const opt = select.querySelector(`option[value="${code}"]`);
                if (opt) {
                    langName = opt.textContent;
                }
            }
            style.prompt = `Convert the following text into a markdown table in ${langName}. Output each cell as [R001-C001 // content] without additional explanations.`;
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

        // Add user message to chat
        this.chatMessages.push({ role: 'user', content: text });
        this.renderChatMessages();
        input.value = '';

        // Disable input while processing
        input.disabled = true;
        const sendBtn = document.getElementById('chat-send');
        if (sendBtn) sendBtn.disabled = true;

        const provider = this.config.postprocessProvider;
        const model = this.config.postprocessModel;
        
        if (!provider || !model) {
            this.showNotification('Please configure AI provider and model in settings', 'error');
            input.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
            return;
        }

        const payload = { note: noteText, messages: this.chatMessages, stream: true, provider, model };
        if (provider === 'lmstudio') {
            payload.host = this.config.lmstudioHost;
            payload.port = this.config.lmstudioPort;
        }
        if (provider === 'ollama') {
            payload.host = this.config.ollamaHost;
            payload.port = this.config.ollamaPort;
        }

        try {
            const response = await authFetch('/api/improve-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok || !response.body) {
                this.showNotification('Chat request failed', 'error');
                input.disabled = false;
                if (sendBtn) sendBtn.disabled = false;
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            const assistantMsg = { role: 'assistant', content: '' };
            this.chatMessages.push(assistantMsg);
            const container = document.getElementById('chat-messages');
            const bubble = document.createElement('div');
            bubble.className = 'chat-message assistant';
            bubble.textContent = '...'; // Show typing indicator
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
                            // Handle error responses
                            if (data.error) {
                                this.showNotification(`Chat error: ${data.error}`, 'error');
                                input.disabled = false;
                                if (sendBtn) sendBtn.disabled = false;
                                return;
                            }
                            // Handle OpenAI streaming format
                            if (data.choices && data.choices[0] && data.choices[0].delta && data.choices[0].delta.content) {
                                const content = data.choices[0].delta.content;
                                // Clear typing indicator on first content
                                if (!assistantMsg.content) {
                                    bubble.textContent = '';
                                }
                                assistantMsg.content += content;
                                bubble.textContent += content;
                                container.scrollTop = container.scrollHeight;
                            }
                            // Handle direct content format (for compatibility)
                            else if (data.content) {
                                // Clear typing indicator on first content
                                if (!assistantMsg.content) {
                                    bubble.textContent = '';
                                }
                                assistantMsg.content += data.content;
                                bubble.textContent += data.content;
                                container.scrollTop = container.scrollHeight;
                            }
                            if (data.done) {
                                bubble.textContent = assistantMsg.content;
                                container.scrollTop = container.scrollHeight;
                                input.disabled = false;
                                if (sendBtn) sendBtn.disabled = false;
                                return;
                            }
                        } catch (e) { continue; }
                    }
                }
            }
            bubble.textContent = assistantMsg.content;
            container.scrollTop = container.scrollHeight;
        } catch (error) {
            this.showNotification(`Chat error: ${error.message}`, 'error');
            console.error('Chat error:', error);
        } finally {
            // Re-enable input
            input.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    setEditorReadOnly(readOnly) {
        const editor = document.getElementById('editor');
        if (!editor) return;
        editor.contentEditable = readOnly ? 'false' : 'true';
        editor.classList.toggle('read-only', readOnly);
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

// Study Modal Functionality
class StudyManager {
    constructor() {
        this.currentQuiz = null;
        this.currentFlashcards = null;
        this.currentQuestionIndex = 0;
        this.currentFlashcardIndex = 0;
        this.userAnswers = [];
        this.selectedProvider = null;
        this.selectedModel = null;
        this.currentNote = null;
        
        // New properties for improved functionality
        this.quizScore = { correct: 0, total: 0 };
        this.isQuizFinished = false;
        this.isGeneratingMore = false;
        this.allQuizQuestions = [];  // Store all generated questions
        this.allFlashcards = [];     // Store all generated flashcards
        this.answeredQuestions = []; // Track if question has been answered
        
        // Study item tracking for continuous updates
        this.currentQuizStudyId = null;    // Track current quiz study item ID
        this.currentFlashcardsStudyId = null; // Track current flashcards study item ID
        
        // Flashcard state variables
        this.globalShowAnswers = false; // Global toggle for showing all answers
        this.currentCardShowAnswer = false; // Current card answer visibility
        
        // Token chunking properties
        this.tokenChunkSize = 50000; // 50k tokens per chunk
        this.currentQuizChunkIndex = 0; // Current chunk for quiz generation
        this.currentFlashcardsChunkIndex = 0; // Current chunk for flashcards generation
        this.noteChunks = []; // Store pre-calculated chunks
        this.chunkPositions = {}; // Store chunk positions per note
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Study button
        document.getElementById('study-btn').addEventListener('click', () => {
            this.openStudyModal();
        });

        // Modal close
        document.getElementById('close-study-modal').addEventListener('click', () => {
            this.closeStudyModal();
        });

        // Tab switching
        document.querySelectorAll('[data-tab]').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.getAttribute('data-tab'));
            });
        });

        // Quiz functionality
        document.getElementById('generate-new-quiz-btn').addEventListener('click', () => {
            this.showQuizSetup();
        });

        document.getElementById('study-saved-quiz-btn').addEventListener('click', () => {
            this.startRandomQuiz();
        });

        document.getElementById('start-quiz-btn').addEventListener('click', () => {
            this.generateQuiz();
        });

        document.getElementById('next-question-btn').addEventListener('click', () => {
            this.nextQuestion();
        });

        document.getElementById('prev-question-btn').addEventListener('click', () => {
            this.prevQuestion();
        });

        document.getElementById('finish-quiz-btn').addEventListener('click', () => {
            this.finishQuiz();
        });

        document.getElementById('save-quiz-btn').addEventListener('click', () => {
            this.saveQuiz();
        });

        document.getElementById('new-quiz-btn').addEventListener('click', () => {
            this.newQuiz();
        });

        // Flashcards functionality
        document.getElementById('generate-new-flashcards-btn').addEventListener('click', () => {
            this.showFlashcardsSetup();
        });

        document.getElementById('study-saved-flashcards-btn').addEventListener('click', () => {
            this.startRandomFlashcards();
        });

        document.getElementById('start-flashcards-btn').addEventListener('click', () => {
            this.generateFlashcards();
        });

        document.getElementById('toggle-answer-btn').addEventListener('click', () => {
            this.toggleAnswer();
        });

        document.getElementById('global-show-answers-btn').addEventListener('click', () => {
            this.toggleGlobalAnswers();
        });

        document.getElementById('next-flashcard-btn').addEventListener('click', () => {
            this.nextFlashcard();
        });

        document.getElementById('prev-flashcard-btn').addEventListener('click', () => {
            this.prevFlashcard();
        });

        document.getElementById('finish-flashcards-btn').addEventListener('click', () => {
            this.finishFlashcards();
        });

        document.getElementById('save-flashcards-btn').addEventListener('click', () => {
            this.saveFlashcards();
        });

        document.getElementById('new-flashcards-btn').addEventListener('click', () => {
            this.newFlashcards();
        });

        // Global delete buttons
        document.getElementById('delete-all-quizzes-btn').addEventListener('click', () => {
            this.deleteAllQuizzes();
        });

        document.getElementById('delete-all-flashcards-btn').addEventListener('click', () => {
            this.deleteAllFlashcards();
        });
    }

    openStudyModal() {
        console.log('Opening study modal...');
        
        // Get current note content and config
        this.currentNote = window.notesApp?.currentNote || null;
        
        if (!this.currentNote) {
            alert('Please open a note first to generate study materials.');
            return;
        }

        console.log('Current note:', this.currentNote?.title);

        this.getConfiguredProvider();
        
        if (!this.selectedProvider) {
            alert('Please configure a post-processing AI provider in settings first (Configuration → Post-process Provider).');
            return;
        }
        
        if (!this.selectedModel) {
            alert(`Please select a model for ${this.selectedProvider} provider in settings first.`);
            return;
        }

        console.log('Provider and model configured successfully');
        document.getElementById('study-modal').style.display = 'flex';
        
        // Set quiz tab as default
        this.switchTab('quiz-tab');
        
        // Initialize chunking for the current note
        this.initializeNoteChunking();
        
        this.loadSavedItems();
    }

    // Token estimation and chunking methods
    estimateTokens(text) {
        // Rough estimation: 1 token ≈ 4 characters for most languages
        // This is a conservative estimate that works reasonably well
        return Math.ceil(text.length / 4);
    }

    initializeNoteChunking() {
        if (!this.currentNote || !this.currentNote.content) {
            this.noteChunks = [];
            return;
        }

        const noteId = this.currentNote.id || this.currentNote.title || 'untitled';
        const content = this.currentNote.content;
        
        // Load saved chunk positions for this note
        this.loadChunkPositions();
        
        // Initialize chunk positions if not exists
        if (!this.chunkPositions[noteId]) {
            this.chunkPositions[noteId] = {
                quiz: 0,
                flashcards: 0
            };
        }
        
        this.currentQuizChunkIndex = this.chunkPositions[noteId].quiz;
        this.currentFlashcardsChunkIndex = this.chunkPositions[noteId].flashcards;
        
        // Split content into chunks based on token estimation
        this.noteChunks = this.createTokenChunks(content);
        
        console.log(`Note chunked into ${this.noteChunks.length} chunks of ~${this.tokenChunkSize} tokens each`);
        console.log(`Quiz will start from chunk ${this.currentQuizChunkIndex + 1}`);
        console.log(`Flashcards will start from chunk ${this.currentFlashcardsChunkIndex + 1}`);
    }

    createTokenChunks(content) {
        const chunks = [];
        const words = content.split(/\s+/);
        let currentChunk = '';
        let currentTokens = 0;
        
        for (const word of words) {
            const wordTokens = this.estimateTokens(word + ' ');
            
            // If adding this word would exceed the limit, start a new chunk
            if (currentTokens + wordTokens > this.tokenChunkSize && currentChunk.length > 0) {
                chunks.push(currentChunk.trim());
                currentChunk = word + ' ';
                currentTokens = wordTokens;
            } else {
                currentChunk += word + ' ';
                currentTokens += wordTokens;
            }
        }
        
        // Add the last chunk if it has content
        if (currentChunk.trim().length > 0) {
            chunks.push(currentChunk.trim());
        }
        
        return chunks;
    }

    getCurrentQuizChunk() {
        if (this.currentQuizChunkIndex >= this.noteChunks.length) {
            // Reset to beginning if we've gone through all chunks
            this.currentQuizChunkIndex = 0;
            this.updateChunkPosition('quiz', 0);
        }
        
        return this.noteChunks[this.currentQuizChunkIndex] || '';
    }

    getCurrentFlashcardsChunk() {
        if (this.currentFlashcardsChunkIndex >= this.noteChunks.length) {
            // Reset to beginning if we've gone through all chunks
            this.currentFlashcardsChunkIndex = 0;
            this.updateChunkPosition('flashcards', 0);
        }
        
        return this.noteChunks[this.currentFlashcardsChunkIndex] || '';
    }

    advanceQuizChunk() {
        this.currentQuizChunkIndex++;
        this.updateChunkPosition('quiz', this.currentQuizChunkIndex);
    }

    advanceFlashcardsChunk() {
        this.currentFlashcardsChunkIndex++;
        this.updateChunkPosition('flashcards', this.currentFlashcardsChunkIndex);
    }

    updateChunkPosition(type, position) {
        const noteId = this.currentNote.id || this.currentNote.title || 'untitled';
        if (!this.chunkPositions[noteId]) {
            this.chunkPositions[noteId] = { quiz: 0, flashcards: 0 };
        }
        this.chunkPositions[noteId][type] = position;
        this.saveChunkPositions();
    }

    saveChunkPositions() {
        const key = `study-chunk-positions-${currentUser || 'default'}`;
        localStorage.setItem(key, JSON.stringify(this.chunkPositions));
    }

    loadChunkPositions() {
        const key = `study-chunk-positions-${currentUser || 'default'}`;
        const saved = localStorage.getItem(key);
        if (saved) {
            try {
                this.chunkPositions = JSON.parse(saved);
            } catch (error) {
                console.error('Error loading chunk positions:', error);
                this.chunkPositions = {};
            }
        } else {
            this.chunkPositions = {};
        }
    }

    closeStudyModal() {
        document.getElementById('study-modal').style.display = 'none';
        this.resetState();
    }

    getConfiguredProvider() {
        // Get the configured provider and model from the notesApp config
        if (!window.notesApp || !window.notesApp.config) {
            console.log('NotesApp config not available');
            return;
        }
        
        const provider = window.notesApp.config.postprocessProvider;
        const model = window.notesApp.config.postprocessModel;
        
        this.selectedProvider = provider;
        this.selectedModel = model;
        
        console.log('Selected provider:', provider, 'model:', model);
    }

    switchTab(tabId) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.style.display = 'none';
        });

        // Remove active class from all buttons
        document.querySelectorAll('[data-tab]').forEach(button => {
            button.classList.remove('btn--primary');
            button.classList.add('btn--outline');
        });

        // Show selected tab
        document.getElementById(tabId).style.display = 'block';

        // Add active class to clicked button
        const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
        activeButton.classList.remove('btn--outline');
        activeButton.classList.add('btn--primary');
    }

    async generateQuiz() {
        const language = document.getElementById('quiz-language').value;
        const level = document.getElementById('quiz-level').value;
        
        if (this.noteChunks.length === 0) {
            alert('The current note is empty. Add some content first.');
            return;
        }

        const currentChunk = this.getCurrentQuizChunk();
        const chunkInfo = `(Chunk ${this.currentQuizChunkIndex + 1} of ${this.noteChunks.length})`;
        
        console.log('Generating quiz with:', { 
            language, 
            level, 
            chunkIndex: this.currentQuizChunkIndex + 1,
            totalChunks: this.noteChunks.length,
            chunkTokens: this.estimateTokens(currentChunk)
        });

        // Show loading with chunk information
        const startBtn = document.getElementById('start-quiz-btn');
        startBtn.textContent = `Generating... ${chunkInfo}`;
        startBtn.disabled = true;

        try {
            // Use the robust backend endpoint like the concept graph
            const response = await authFetch('/api/generate-quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: currentChunk,
                    difficulty: level,
                    num_questions: 10,
                    note_id: this.currentNote.id
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Quiz generation failed');
            }

            const data = await response.json();
            
            if (data.questions && data.questions.length > 0) {
                // Shuffle questions and answers for randomization
                this.currentQuiz = this.shuffleQuiz(data.questions);
                console.log('Successfully generated quiz with', this.currentQuiz.length, 'questions');
                
                // Advance to next chunk for next generation
                this.advanceQuizChunk();
                
                // Update button to show next chunk info
                const nextChunkIndex = this.currentQuizChunkIndex >= this.noteChunks.length ? 1 : this.currentQuizChunkIndex + 1;
                const nextChunkInfo = `(Next: Chunk ${nextChunkIndex} of ${this.noteChunks.length})`;
                startBtn.textContent = `Generate Quiz ${nextChunkInfo}`;
                
                // If quiz was saved to database (has study_id), refresh saved items if user is viewing them
                if (data.study_id) {
                    console.log('Quiz saved to database with ID:', data.study_id);
                    this.currentQuizStudyId = data.study_id; // Store the study ID for future updates
                    // Check if user is currently viewing saved items tab
                    const savedTab = document.getElementById('saved-tab');
                    if (savedTab && !savedTab.style.display.includes('none')) {
                        // Refresh saved items list to show the new quiz
                        this.loadSavedItems();
                    }
                }
                
                this.startQuiz();
            } else {
                throw new Error('No quiz questions were generated');
            }
        } catch (error) {
            console.error('Error generating quiz:', error);
            alert(`Error generating quiz: ${error.message}. Please check the console for details and try again.`);
        } finally {
            if (!this.currentQuiz) {
                // Only reset if quiz generation failed
                const nextChunkIndex = this.currentQuizChunkIndex >= this.noteChunks.length ? 1 : this.currentQuizChunkIndex + 1;
                const nextChunkInfo = `(Next: Chunk ${nextChunkIndex} of ${this.noteChunks.length})`;
                startBtn.textContent = `Generate Quiz ${nextChunkInfo}`;
            }
            startBtn.disabled = false;
        }
    }

    async generateFlashcards() {
        const language = document.getElementById('flashcards-language').value;
        const level = document.getElementById('flashcards-level').value;
        
        if (this.noteChunks.length === 0) {
            alert('The current note is empty. Add some content first.');
            return;
        }

        const currentChunk = this.getCurrentFlashcardsChunk();
        const chunkInfo = `(Chunk ${this.currentFlashcardsChunkIndex + 1} of ${this.noteChunks.length})`;
        
        console.log('Generating flashcards with:', { 
            language, 
            level, 
            chunkIndex: this.currentFlashcardsChunkIndex + 1,
            totalChunks: this.noteChunks.length,
            chunkTokens: this.estimateTokens(currentChunk)
        });

        // Show loading with chunk information
        const startBtn = document.getElementById('start-flashcards-btn');
        startBtn.textContent = `Generating... ${chunkInfo}`;
        startBtn.disabled = true;

        try {
            // Use the robust backend endpoint like the concept graph
            const response = await authFetch('/api/generate-flashcards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: currentChunk,
                    num_cards: 10,
                    note_id: this.currentNote.id
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Flashcards generation failed');
            }

            const data = await response.json();
            
            if (data.flashcards && data.flashcards.length > 0) {
                // Shuffle flashcards for randomization and convert format
                const shuffledFlashcards = this.shuffleFlashcards(data.flashcards);
                this.currentFlashcards = shuffledFlashcards.map(card => ({
                    concept: card.front,
                    description: card.back
                }));
                console.log('Successfully generated flashcards with', this.currentFlashcards.length, 'cards');
                
                // Advance to next chunk for next generation
                this.advanceFlashcardsChunk();
                
                // Update button to show next chunk info
                const nextChunkIndex = this.currentFlashcardsChunkIndex >= this.noteChunks.length ? 1 : this.currentFlashcardsChunkIndex + 1;
                const nextChunkInfo = `(Next: Chunk ${nextChunkIndex} of ${this.noteChunks.length})`;
                startBtn.textContent = `Generate Flashcards ${nextChunkInfo}`;
                
                // If flashcards were saved to database (has study_id), refresh saved items if user is viewing them
                if (data.study_id) {
                    console.log('Flashcards saved to database with ID:', data.study_id);
                    this.currentFlashcardsStudyId = data.study_id; // Store the study ID for future updates
                    // Check if user is currently viewing saved items tab
                    const savedTab = document.getElementById('saved-tab');
                    if (savedTab && !savedTab.style.display.includes('none')) {
                        // Refresh saved items list to show the new flashcards
                        this.loadSavedItems();
                    }
                }
                
                this.startFlashcards();
            } else {
                throw new Error('No flashcards were generated');
            }
        } catch (error) {
            console.error('Error generating flashcards:', error);
            alert(`Error generating flashcards: ${error.message}. Please check the console for details and try again.`);
        } finally {
            if (!this.currentFlashcards) {
                // Only reset if flashcards generation failed
                const nextChunkIndex = this.currentFlashcardsChunkIndex >= this.noteChunks.length ? 1 : this.currentFlashcardsChunkIndex + 1;
                const nextChunkInfo = `(Next: Chunk ${nextChunkIndex} of ${this.noteChunks.length})`;
                startBtn.textContent = `Generate Flashcards ${nextChunkInfo}`;
            }
            startBtn.disabled = false;
        }
    }

    startQuiz() {
        document.getElementById('quiz-setup').classList.add('hidden');
        document.getElementById('quiz-interface').classList.remove('hidden');
        
        this.currentQuestionIndex = 0;
        this.userAnswers = new Array(this.currentQuiz.length);
        this.answeredQuestions = new Array(this.currentQuiz.length).fill(false);
        this.quizScore = { correct: 0, total: 0 };
        this.isQuizFinished = false;
        this.allQuizQuestions = [...this.currentQuiz]; // Initialize with current questions
        
        this.showQuestion();
    }

    showQuestion() {
        const question = this.currentQuiz[this.currentQuestionIndex];
        document.getElementById('quiz-question-counter').textContent = 
            `Question ${this.currentQuestionIndex + 1} of ${this.currentQuiz.length}`;
        document.getElementById('quiz-question-text').textContent = question.question;
        
        const answersContainer = document.getElementById('quiz-answers');
        answersContainer.innerHTML = '';
        
        question.answers.forEach((answer, index) => {
            const answerDiv = document.createElement('div');
            answerDiv.className = 'quiz-answer';
            answerDiv.textContent = answer;
            answerDiv.dataset.index = index;
            
            answerDiv.addEventListener('click', () => {
                this.selectAnswer(index);
            });
            
            answersContainer.appendChild(answerDiv);
        });
        
        // Clear previous feedback
        this.clearAnswerFeedback();
        
        // Update navigation buttons
        document.getElementById('prev-question-btn').disabled = this.currentQuestionIndex === 0;
        document.getElementById('next-question-btn').disabled = true;
        
        if (this.currentQuestionIndex === this.currentQuiz.length - 1) {
            document.getElementById('next-question-btn').classList.add('hidden');
            document.getElementById('finish-quiz-btn').classList.remove('hidden');
        } else {
            document.getElementById('next-question-btn').classList.remove('hidden');
            document.getElementById('finish-quiz-btn').classList.add('hidden');
        }
        
        // Show previous answer if exists
        if (this.userAnswers[this.currentQuestionIndex] !== undefined) {
            this.selectAnswer(this.userAnswers[this.currentQuestionIndex], false);
            this.showAnswerFeedback();
        }
    }

    selectAnswer(answerIndex, updateAnswer = true) {
        const question = this.currentQuiz[this.currentQuestionIndex];
        
        // Prevent changing answer if already answered
        if (this.answeredQuestions[this.currentQuestionIndex] && updateAnswer) {
            return;
        }
        
        // Remove previous selections
        document.querySelectorAll('.quiz-answer').forEach(answer => {
            answer.classList.remove('selected', 'correct', 'incorrect');
        });
        
        // Add selection to clicked answer
        const selectedAnswer = document.querySelector(`[data-index="${answerIndex}"]`);
        selectedAnswer.classList.add('selected');
        
        if (updateAnswer) {
            this.userAnswers[this.currentQuestionIndex] = answerIndex;
            this.answeredQuestions[this.currentQuestionIndex] = true;
            
            // Show immediate feedback
            this.showAnswerFeedback();
            
            // Update score
            const correctIndex = question.correct_answer !== undefined ? question.correct_answer : question.correct;
            if (answerIndex === correctIndex) {
                if (this.quizScore.correct <= this.currentQuestionIndex) {
                    this.quizScore.correct++;
                }
            }
            this.quizScore.total = Math.max(this.quizScore.total, this.currentQuestionIndex + 1);
        }
        
        // Enable next button
        document.getElementById('next-question-btn').disabled = false;
        document.getElementById('finish-quiz-btn').disabled = false;
    }

    showAnswerFeedback() {
        const question = this.currentQuiz[this.currentQuestionIndex];
        const userAnswer = this.userAnswers[this.currentQuestionIndex];
        const correctIndex = question.correct_answer !== undefined ? question.correct_answer : question.correct;
        
        const answers = document.querySelectorAll('.quiz-answer');
        
        answers.forEach((answerEl, index) => {
            if (index === correctIndex) {
                answerEl.classList.add('correct');
            } else if (index === userAnswer && index !== correctIndex) {
                answerEl.classList.add('incorrect');
            }
        });
        
        // Show feedback message
        this.showFeedbackMessage(userAnswer === correctIndex, question.answers[correctIndex]);
    }

    showFeedbackMessage(isCorrect, correctAnswer) {
        // Remove existing feedback
        const existingFeedback = document.querySelector('.answer-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = `answer-feedback ${isCorrect ? 'correct' : 'incorrect'}`;
        
        if (isCorrect) {
            feedbackDiv.innerHTML = `<i class="fas fa-check"></i> Correct!`;
        } else {
            feedbackDiv.innerHTML = `<i class="fas fa-times"></i> Incorrect. The correct answer is: <strong>${correctAnswer}</strong>`;
        }
        
        document.querySelector('.quiz-question').appendChild(feedbackDiv);
    }

    clearAnswerFeedback() {
        const existingFeedback = document.querySelector('.answer-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
    }

    async nextQuestion() {
        if (this.currentQuestionIndex < this.currentQuiz.length - 1) {
            this.currentQuestionIndex++;
            
            // Generate more questions when reaching question 9 (index 8)
            if (this.currentQuestionIndex === 8 && !this.isGeneratingMore) {
                this.generateMoreQuestions();
            }
            
            this.showQuestion();
        }
    }

    async generateMoreQuestions() {
        if (this.isGeneratingMore) return;
        
        this.isGeneratingMore = true;
        console.log('Pre-generating more questions...');
        
        try {
            const level = document.getElementById('quiz-level').value;
            const currentChunk = this.getCurrentQuizChunk();
            
            if (!currentChunk) {
                console.log('No more content chunks available for quiz generation');
                return;
            }
            
            console.log(`Generating additional questions from chunk ${this.currentQuizChunkIndex + 1}`);
            
            // Use the robust backend endpoint
            const response = await authFetch('/api/generate-quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: currentChunk,
                    difficulty: level,
                    num_questions: 10,
                    note_id: this.currentNote.id
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Quiz generation failed');
            }

            const data = await response.json();
            
            if (data.questions && data.questions.length > 0) {
                this.allQuizQuestions = [...this.allQuizQuestions, ...data.questions];
                console.log('Generated', data.questions.length, 'additional questions');
                
                // DO NOT update existing study items - let each generation create its own
                // This prevents the mixing of questions from different quiz sessions
                console.log('New quiz questions saved as separate study item');
                
                // Advance to next chunk for future generations
                this.advanceQuizChunk();
            }
        } catch (error) {
            console.error('Error generating additional questions:', error);
        } finally {
            this.isGeneratingMore = false;
        }
    }

    async generateMoreFlashcards() {
        if (this.isGeneratingMore) return;
        
        this.isGeneratingMore = true;
        console.log('Pre-generating more flashcards...');
        
        try {
            const currentChunk = this.getCurrentFlashcardsChunk();
            
            if (!currentChunk) {
                console.log('No more content chunks available for flashcards generation');
                return;
            }
            
            console.log(`Generating additional flashcards from chunk ${this.currentFlashcardsChunkIndex + 1}`);
            
            // Use the robust backend endpoint
            const response = await authFetch('/api/generate-flashcards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: currentChunk,
                    num_cards: 10
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Flashcards generation failed');
            }

            const data = await response.json();
            
            if (data.flashcards && data.flashcards.length > 0) {
                // Convert to the format expected by the flashcards interface
                const newFlashcards = data.flashcards.map(card => ({
                    concept: card.front,
                    description: card.back
                }));
                this.allFlashcards = [...this.allFlashcards, ...newFlashcards];
                console.log('Generated', newFlashcards.length, 'additional flashcards');
                
                // DO NOT update existing study items - let each generation create its own
                // This prevents the mixing of flashcards from different sessions
                console.log('New flashcards saved as separate study item');
                
                // Advance to next chunk for future generations
                this.advanceFlashcardsChunk();
            }
        } catch (error) {
            console.error('Error generating additional flashcards:', error);
        } finally {
            this.isGeneratingMore = false;
        }
    }

    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.showQuestion();
        }
    }

    finishQuiz() {
        this.isQuizFinished = true;
        // Instead of showing results, return to quiz options
        this.resetQuizState();
    }

    async saveQuiz() {
        try {
            const quizData = {
                title: this.currentNote.title || 'Untitled Quiz',
                questions: this.currentQuiz,
                userAnswers: this.userAnswers,
                timestamp: new Date().toISOString(),
                language: document.getElementById('quiz-language').value,
                level: document.getElementById('quiz-level').value
            };

            await this.saveStudyItem('quiz', quizData);
            alert('Quiz saved successfully!');
            this.loadSavedItems();
        } catch (error) {
            console.error('Error saving quiz:', error);
            alert('Error saving quiz.');
        }
    }

    async loadSavedQuiz() {
        try {
            // Reset to quiz options
            this.resetQuizState();
        } catch (error) {
            console.error('Error loading saved quiz:', error);
            alert('Error loading saved quizzes.');
        }
    }

    newQuiz() {
        this.resetQuizState();
    }

    startFlashcards() {
        document.getElementById('flashcards-setup').classList.add('hidden');
        document.getElementById('flashcards-interface').classList.remove('hidden');
        
        this.currentFlashcardIndex = 0;
        this.globalShowAnswers = false;
        this.currentCardShowAnswer = false;
        this.allFlashcards = [...this.currentFlashcards]; // Initialize with current flashcards
        
        // Reset global toggle button state
        const globalBtn = document.getElementById('global-show-answers-btn');
        const globalIcon = document.getElementById('global-eye-icon');
        globalBtn.classList.remove('active');
        globalIcon.className = 'fas fa-eye';
        
        this.showFlashcard();
    }

    showFlashcard() {
        const flashcard = this.currentFlashcards[this.currentFlashcardIndex];
        document.getElementById('flashcard-counter').textContent = 
            `Card ${this.currentFlashcardIndex + 1} of ${this.currentFlashcards.length}`;
        
        document.getElementById('flashcard-concept').textContent = flashcard.concept;
        document.getElementById('flashcard-description').textContent = flashcard.description;
        
        // Update answer visibility based on global setting or individual card setting
        const shouldShowAnswer = this.globalShowAnswers || this.currentCardShowAnswer;
        const answerElement = document.getElementById('flashcard-answer');
        const eyeIcon = document.getElementById('card-eye-icon');
        const toggleBtn = document.getElementById('toggle-answer-btn');
        
        if (shouldShowAnswer) {
            answerElement.classList.remove('hidden');
            eyeIcon.className = 'fas fa-eye-slash';
            toggleBtn.classList.add('active');
        } else {
            answerElement.classList.add('hidden');
            eyeIcon.className = 'fas fa-eye';
            toggleBtn.classList.remove('active');
        }
        
        // Update navigation buttons
        document.getElementById('prev-flashcard-btn').disabled = this.currentFlashcardIndex === 0;
        document.getElementById('next-flashcard-btn').disabled = false;
        
        if (this.currentFlashcardIndex === this.currentFlashcards.length - 1) {
            document.getElementById('next-flashcard-btn').classList.add('hidden');
            document.getElementById('finish-flashcards-btn').classList.remove('hidden');
        } else {
            document.getElementById('next-flashcard-btn').classList.remove('hidden');
            document.getElementById('finish-flashcards-btn').classList.add('hidden');
        }
    }

    toggleAnswer() {
        this.currentCardShowAnswer = !this.currentCardShowAnswer;
        this.showFlashcard();
    }

    toggleGlobalAnswers() {
        this.globalShowAnswers = !this.globalShowAnswers;
        const globalBtn = document.getElementById('global-show-answers-btn');
        const globalIcon = document.getElementById('global-eye-icon');
        
        if (this.globalShowAnswers) {
            globalBtn.classList.add('active');
            globalIcon.className = 'fas fa-eye-slash';
        } else {
            globalBtn.classList.remove('active');
            globalIcon.className = 'fas fa-eye';
        }
        
        // Reset individual card state when global toggle is used
        this.currentCardShowAnswer = false;
        this.showFlashcard();
    }

    nextFlashcard() {
        if (this.currentFlashcardIndex < this.currentFlashcards.length - 1) {
            this.currentFlashcardIndex++;
            
            // Reset individual card answer visibility when moving to next card
            this.currentCardShowAnswer = false;
            
            // Generate more flashcards when reaching card 9 (index 8)
            if (this.currentFlashcardIndex === 8 && !this.isGeneratingMore) {
                this.generateMoreFlashcards();
            }
            
            this.showFlashcard();
        }
    }

    prevFlashcard() {
        if (this.currentFlashcardIndex > 0) {
            this.currentFlashcardIndex--;
            
            // Reset individual card answer visibility when moving to previous card
            this.currentCardShowAnswer = false;
            
            this.showFlashcard();
        }
    }

    finishFlashcards() {
        document.getElementById('flashcards-interface').classList.add('hidden');
        document.getElementById('flashcards-results').classList.remove('hidden');
        
        // Check if there are more chunks available for generating more flashcards
        const hasMoreContent = this.currentFlashcardsChunkIndex < this.noteChunks.length;
        
        // Update the results HTML with action buttons
        const resultsDiv = document.getElementById('flashcards-results');
        resultsDiv.innerHTML = `
            <h4>Flashcards Complete!</h4>
            <p>You've completed ${this.currentFlashcards.length} flashcards.</p>
            <div class="flashcards-results-actions">
                ${hasMoreContent ? `<button class="btn btn--success" id="generate-more-flashcards-btn">Generate More Flashcards</button>` : ''}
                <button class="btn btn--primary" id="retry-flashcards-btn">Try Again</button>
                <button class="btn btn--secondary" id="load-saved-flashcards-btn">Saved Flashcards</button>
                <button class="btn btn--outline" id="new-flashcards-btn">Generate New</button>
                <button class="btn btn--tertiary" id="save-flashcards-btn">Save Flashcards</button>
            </div>
        `;
        
        // Re-attach event listeners
        if (hasMoreContent) {
            document.getElementById('generate-more-flashcards-btn').addEventListener('click', () => this.generateMoreFlashcardsAndContinue());
        }
        document.getElementById('retry-flashcards-btn').addEventListener('click', () => this.retryFlashcards());
        document.getElementById('load-saved-flashcards-btn').addEventListener('click', () => this.loadSavedFlashcards());
        document.getElementById('new-flashcards-btn').addEventListener('click', () => this.newFlashcards());
        document.getElementById('save-flashcards-btn').addEventListener('click', () => this.saveFlashcards());
    }

    async saveFlashcards() {
        try {
            const flashcardsData = {
                title: this.currentNote.title || 'Untitled Flashcards',
                flashcards: this.currentFlashcards,
                timestamp: new Date().toISOString(),
                language: document.getElementById('flashcards-language').value,
                level: document.getElementById('flashcards-level').value
            };

            await this.saveStudyItem('flashcards', flashcardsData);
            alert('Flashcards saved successfully!');
            this.loadSavedItems();
        } catch (error) {
            console.error('Error saving flashcards:', error);
            alert('Error saving flashcards.');
        }
    }

    async generateMoreFlashcardsAndContinue() {
        if (this.currentFlashcardsChunkIndex >= this.noteChunks.length) {
            alert('No more content available for generating additional flashcards.');
            return;
        }

        const generateBtn = document.getElementById('generate-more-flashcards-btn');
        const originalText = generateBtn.textContent;
        generateBtn.textContent = 'Generating...';
        generateBtn.disabled = true;

        try {
            const currentChunk = this.getCurrentFlashcardsChunk();
            
            console.log(`Generating more flashcards from chunk ${this.currentFlashcardsChunkIndex + 1}`);
            
            const response = await authFetch('/api/generate-flashcards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: currentChunk,
                    num_cards: 10
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Flashcards generation failed');
            }

            const data = await response.json();
            
            if (data.flashcards && data.flashcards.length > 0) {
                // Convert and shuffle new flashcards
                const newFlashcards = data.flashcards.map(card => ({
                    concept: card.front,
                    description: card.back
                }));
                const shuffledNewFlashcards = this.shuffleFlashcards(newFlashcards);
                
                // Start new session with new flashcards
                this.currentFlashcards = shuffledNewFlashcards;
                this.allFlashcards = [...this.allFlashcards, ...shuffledNewFlashcards];
                
                // DO NOT update existing study items - let each generation create its own
                // This prevents the mixing of flashcards from different sessions
                console.log('New flashcards saved as separate study item');
                
                // Reset for new session
                this.currentFlashcardIndex = 0;
                this.globalShowAnswers = false;
                this.currentCardShowAnswer = false;
                
                // Advance to next chunk for future generations
                this.advanceFlashcardsChunk();
                
                console.log('Generated', shuffledNewFlashcards.length, 'new flashcards');
                
                // Switch back to flashcards interface
                document.getElementById('flashcards-results').classList.add('hidden');
                document.getElementById('flashcards-interface').classList.remove('hidden');
                
                // Reset global toggle button state
                const globalBtn = document.getElementById('global-show-answers-btn');
                const globalIcon = document.getElementById('global-eye-icon');
                globalBtn.classList.remove('active');
                globalIcon.className = 'fas fa-eye';
                
                this.showFlashcard();
            } else {
                throw new Error('No new flashcards were generated');
            }
        } catch (error) {
            console.error('Error generating more flashcards:', error);
            alert(`Error generating more flashcards: ${error.message}`);
        } finally {
            generateBtn.textContent = originalText;
            generateBtn.disabled = false;
        }
    }

    retryFlashcards() {
        // Shuffle the same flashcards again and restart
        this.currentFlashcards = this.shuffleFlashcards(this.allFlashcards || this.currentFlashcards);
        this.currentFlashcardIndex = 0;
        this.isCardFlipped = false;
        
        document.getElementById('flashcards-results').classList.add('hidden');
        document.getElementById('flashcards-interface').classList.remove('hidden');
        this.showFlashcard();
    }

    async loadSavedFlashcards() {
        try {
            // Switch to saved items tab to show available flashcards
            this.showTab('saved-items');
            // Close the results modal
            document.getElementById('flashcards-results').classList.add('hidden');
            document.getElementById('flashcards-setup').classList.remove('hidden');
        } catch (error) {
            console.error('Error loading saved flashcards:', error);
            alert('Error loading saved flashcards.');
        }
    }

    newFlashcards() {
        this.resetFlashcardsState();
        document.getElementById('flashcards-results').classList.add('hidden');
        document.getElementById('flashcards-setup').classList.remove('hidden');
    }

    async saveStudyItem(type, data) {
        const filename = `${this.currentNote.title || 'untitled'}_${type}_${Date.now()}.json`;
        
        const response = await authFetch('/api/save-study-item', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename,
                type,
                data
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
    }

    async loadSavedItems() {
        try {
            const response = await authFetch('/api/get-study-items');
            if (response.ok) {
                const items = await response.json();
                this.renderSavedItems(items);
            }
        } catch (error) {
            console.error('Error loading saved items:', error);
        }
    }

    renderSavedItems(items) {
        const quizList = document.getElementById('saved-quiz-list');
        const flashcardsList = document.getElementById('saved-flashcards-list');
        
        // Filter items by type, including individual items
        const quizzes = items.filter(item => item.type === 'quiz' || item.type === 'quiz_individual');
        const flashcards = items.filter(item => item.type === 'flashcards' || item.type === 'flashcards_individual');
        
        // Show/hide delete all buttons based on whether there are items
        const deleteAllQuizzesBtn = document.getElementById('delete-all-quizzes-btn');
        const deleteAllFlashcardsBtn = document.getElementById('delete-all-flashcards-btn');
        
        if (deleteAllQuizzesBtn) {
            deleteAllQuizzesBtn.style.display = quizzes.length > 0 ? 'inline-flex' : 'none';
        }
        
        if (deleteAllFlashcardsBtn) {
            deleteAllFlashcardsBtn.style.display = flashcards.length > 0 ? 'inline-flex' : 'none';
        }
        
        if (quizzes.length === 0) {
            quizList.innerHTML = '<p class="no-items">No saved quizzes yet.</p>';
        } else {
            quizList.innerHTML = quizzes.map(quiz => this.renderSavedItem(quiz)).join('');
        }
        
        if (flashcards.length === 0) {
            flashcardsList.innerHTML = '<p class="no-items">No saved flashcards yet.</p>';
        } else {
            flashcardsList.innerHTML = flashcards.map(fc => this.renderSavedItem(fc)).join('');
        }
    }

    renderSavedItem(item) {
        const date = new Date(item.created_at || item.timestamp).toLocaleDateString();
        const itemId = item.id || item.filename;
        
        // Handle individual items vs sets
        let itemCount = item.item_count || 0;
        let itemLabel = 'items';
        
        if (item.type === 'quiz' || item.type === 'quiz_individual') {
            if (item.type === 'quiz_individual') {
                // Individual question
                itemCount = 1;
                itemLabel = 'question';
            } else {
                // Set of questions
                const questions = item.content?.questions || item.questions || [];
                itemCount = questions.length || itemCount;
                itemLabel = itemCount === 1 ? 'question' : 'questions';
            }
        } else if (item.type === 'flashcards' || item.type === 'flashcards_individual') {
            if (item.type === 'flashcards_individual') {
                // Individual flashcard
                itemCount = 1;
                itemLabel = 'card';
            } else {
                // Set of flashcards
                const flashcards = item.content?.flashcards || item.flashcards || [];
                itemCount = flashcards.length || itemCount;
                itemLabel = itemCount === 1 ? 'card' : 'cards';
            }
        }
        
        // Clean up the display type for UI
        const displayType = item.type.replace('_individual', '');
        
        return `
            <div class="saved-item">
                <div class="saved-item-info">
                    <div class="saved-item-title">${item.title}</div>
                    <div class="saved-item-meta">${date} • ${itemCount} ${itemLabel}</div>
                </div>
                <div class="saved-item-actions">
                    <button class="btn btn--outline btn--sm" onclick="studyManager.reviewItem('${itemId}', '${displayType}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn--outline btn--sm" onclick="studyManager.deleteItem('${itemId}', '${item.type}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    async reviewItem(itemId, type) {
        try {
            // Check if itemId is numeric (database ID) or string (filename for backward compatibility)
            const endpoint = /^\d+$/.test(itemId) ? `/api/get-study-item/${itemId}` : `/api/get-study-item/${itemId}`;
            
            const response = await authFetch(endpoint);
            if (response.ok) {
                const data = await response.json();
                
                if (type === 'quiz') {
                    // Handle both individual questions and question sets
                    let allQuestions;
                    if (data.content?.question) {
                        // Individual question - wrap in array
                        allQuestions = [data.content.question];
                    } else {
                        // Set of questions
                        allQuestions = data.content?.questions || data.questions;
                    }
                    
                    if (allQuestions && allQuestions.length > 0) {
                        // Show question count selector for quizzes
                        this.showQuestionCountSelector(allQuestions, itemId);
                    } else {
                        alert('No questions found in this item.');
                    }
                } else if (type === 'flashcards') {
                    // Handle both individual flashcards and flashcard sets
                    let allFlashcards;
                    if (data.content?.flashcard) {
                        // Individual flashcard - wrap in array and convert format
                        const flashcard = data.content.flashcard;
                        allFlashcards = [{
                            concept: flashcard.front,
                            description: flashcard.back
                        }];
                    } else {
                        // Set of flashcards - convert format
                        const flashcards = data.content?.flashcards || data.flashcards;
                        allFlashcards = flashcards ? flashcards.map(card => ({
                            concept: card.front,
                            description: card.back
                        })) : [];
                    }
                    
                    if (allFlashcards && allFlashcards.length > 0) {
                        this.currentFlashcards = allFlashcards;
                        this.switchToFlashcardsInterface();
                        this.startFlashcards();
                    } else {
                        alert('No flashcards found in this item.');
                    }
                }
            } else {
                throw new Error('Failed to load study item');
            }
        } catch (error) {
            console.error('Error reviewing item:', error);
            alert('Error loading study item.');
        }
    }

    showQuestionCountSelector(allQuestions, itemId) {
        const totalQuestions = allQuestions.length;
        
        // Create modal content for question count selection
        const modalContent = `
            <div class="question-count-modal" style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 1001;
                min-width: 300px;
                text-align: center;
            ">
                <h4>Select Number of Questions</h4>
                <p>This quiz has ${totalQuestions} questions total.</p>
                <div style="margin: 20px 0;">
                    <label for="question-count-input" style="display: block; margin-bottom: 10px;">
                        How many questions do you want? (1-${totalQuestions})
                    </label>
                    <input 
                        type="number" 
                        id="question-count-input" 
                        min="1" 
                        max="${totalQuestions}" 
                        value="${Math.min(10, totalQuestions)}"
                        style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; width: 100px;"
                    >
                </div>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="start-selected-quiz-btn" class="btn btn--primary">Start Quiz</button>
                    <button id="cancel-quiz-selection-btn" class="btn btn--outline">Cancel</button>
                </div>
            </div>
            <div class="question-count-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
            "></div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // Add event listeners
        document.getElementById('start-selected-quiz-btn').addEventListener('click', () => {
            const selectedCount = parseInt(document.getElementById('question-count-input').value);
            if (selectedCount > 0 && selectedCount <= totalQuestions) {
                this.startQuizWithSelectedQuestions(allQuestions, selectedCount);
                this.removeQuestionCountModal();
            } else {
                alert(`Please enter a number between 1 and ${totalQuestions}`);
            }
        });
        
        document.getElementById('cancel-quiz-selection-btn').addEventListener('click', () => {
            this.removeQuestionCountModal();
        });
        
        // Close on overlay click
        document.querySelector('.question-count-overlay').addEventListener('click', () => {
            this.removeQuestionCountModal();
        });
        
        // Focus on input and select text
        const input = document.getElementById('question-count-input');
        input.focus();
        input.select();
        
        // Allow Enter key to start quiz
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('start-selected-quiz-btn').click();
            }
        });
    }

    removeQuestionCountModal() {
        const modal = document.querySelector('.question-count-modal');
        const overlay = document.querySelector('.question-count-overlay');
        if (modal) modal.remove();
        if (overlay) overlay.remove();
    }

    startQuizWithSelectedQuestions(allQuestions, selectedCount) {
        // Shuffle all questions and take the requested number
        const shuffledQuestions = this.shuffleQuiz([...allQuestions]);
        this.currentQuiz = shuffledQuestions.slice(0, selectedCount);
        
        console.log(`Starting quiz with ${selectedCount} questions out of ${allQuestions.length} total`);
        
        // Switch to quiz tab but go directly to the quiz interface
        this.switchToQuizInterface();
        this.startQuiz();
    }

    showRandomQuizCountSelector(allQuestions) {
        const totalQuestions = allQuestions.length;
        
        // Count unique sources
        const uniqueSources = new Set();
        allQuestions.forEach(q => {
            if (q._source_title) {
                uniqueSources.add(q._source_title);
            }
        });
        
        const sourceInfo = uniqueSources.size > 0 ? 
            `Questions mixed from ${uniqueSources.size} recent quiz sets` : 
            'Questions from your saved quizzes';
        
        // Create modal content for question count selection
        const modalContent = `
            <div class="question-count-modal" style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 1001;
                min-width: 350px;
                text-align: center;
            ">
                <h4>Mixed Quiz Selection</h4>
                <p><strong>${totalQuestions} questions available</strong></p>
                <p style="font-size: 0.9em; color: #666; margin-bottom: 15px;">${sourceInfo}</p>
                <div style="margin: 20px 0;">
                    <label for="random-question-count-input" style="display: block; margin-bottom: 10px;">
                        How many questions do you want to study? (1-${Math.min(totalQuestions, 30)})
                    </label>
                    <input 
                        type="number" 
                        id="random-question-count-input" 
                        min="1" 
                        max="${Math.min(totalQuestions, 30)}" 
                        value="${Math.min(10, totalQuestions)}"
                        style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; width: 100px;"
                    >
                </div>
                ${totalQuestions > 30 ? '<p style="font-size: 0.8em; color: #888;">Limited to 30 questions max to prevent overwhelming</p>' : ''}
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="start-random-quiz-btn" class="btn btn--primary">Start Mixed Quiz</button>
                    <button id="cancel-random-quiz-btn" class="btn btn--outline">Cancel</button>
                </div>
            </div>
            <div class="question-count-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
            "></div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // Add event listeners
        document.getElementById('start-random-quiz-btn').addEventListener('click', () => {
            const selectedCount = parseInt(document.getElementById('random-question-count-input').value);
            const maxAllowed = Math.min(totalQuestions, 30);
            if (selectedCount > 0 && selectedCount <= maxAllowed) {
                this.startRandomQuizWithSelectedQuestions(allQuestions, selectedCount);
                this.removeRandomQuizCountModal();
            } else {
                alert(`Please enter a number between 1 and ${maxAllowed}`);
            }
        });
        
        document.getElementById('cancel-random-quiz-btn').addEventListener('click', () => {
            this.removeRandomQuizCountModal();
        });
        
        // Close on overlay click
        document.querySelector('.question-count-overlay').addEventListener('click', () => {
            this.removeRandomQuizCountModal();
        });
        
        // Focus on input and select text
        const input = document.getElementById('random-question-count-input');
        input.focus();
        input.select();
        
        // Allow Enter key to start quiz
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('start-random-quiz-btn').click();
            }
        });
    }

    removeRandomQuizCountModal() {
        const modal = document.querySelector('.question-count-modal');
        const overlay = document.querySelector('.question-count-overlay');
        if (modal) modal.remove();
        if (overlay) overlay.remove();
    }

    startRandomQuizWithSelectedQuestions(allQuestions, selectedCount) {
        // Set up the quiz with shuffled questions
        this.currentQuiz = this.shuffleQuiz([...allQuestions]).slice(0, selectedCount);
        this.allQuizQuestions = [...this.currentQuiz];
        this.currentQuizStudyId = null; // No specific study ID since it's mixed content
        
        console.log(`Starting random quiz with ${selectedCount} questions from saved content`);
        
        // Switch directly to quiz interface and start
        this.switchToQuizInterface();
        this.startQuiz();
    }

    showRandomFlashcardCountSelector(allFlashcards) {
        const totalFlashcards = allFlashcards.length;
        
        // Count unique sources
        const uniqueSources = new Set();
        allFlashcards.forEach(f => {
            if (f._source_title) {
                uniqueSources.add(f._source_title);
            }
        });
        
        const sourceInfo = uniqueSources.size > 0 ? 
            `Flashcards mixed from ${uniqueSources.size} recent flashcard sets` : 
            'Flashcards from your saved sets';
        
        // Create modal content for flashcard count selection
        const modalContent = `
            <div class="question-count-modal" style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 1001;
                min-width: 350px;
                text-align: center;
            ">
                <h4>Mixed Flashcards Selection</h4>
                <p><strong>${totalFlashcards} flashcards available</strong></p>
                <p style="font-size: 0.9em; color: #666; margin-bottom: 15px;">${sourceInfo}</p>
                <div style="margin: 20px 0;">
                    <label for="random-flashcard-count-input" style="display: block; margin-bottom: 10px;">
                        How many flashcards do you want to study? (1-${Math.min(totalFlashcards, 50)})
                    </label>
                    <input 
                        type="number" 
                        id="random-flashcard-count-input" 
                        min="1" 
                        max="${Math.min(totalFlashcards, 50)}" 
                        value="${Math.min(15, totalFlashcards)}"
                        style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; width: 100px;"
                    >
                </div>
                ${totalFlashcards > 50 ? '<p style="font-size: 0.8em; color: #888;">Limited to 50 flashcards max to prevent overwhelming</p>' : ''}
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="start-random-flashcards-btn" class="btn btn--primary">Start Mixed Flashcards</button>
                    <button id="cancel-random-flashcards-btn" class="btn btn--outline">Cancel</button>
                </div>
            </div>
            <div class="question-count-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
            "></div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // Add event listeners
        document.getElementById('start-random-flashcards-btn').addEventListener('click', () => {
            const selectedCount = parseInt(document.getElementById('random-flashcard-count-input').value);
            const maxAllowed = Math.min(totalFlashcards, 50);
            if (selectedCount > 0 && selectedCount <= maxAllowed) {
                this.startRandomFlashcardsWithSelectedCount(allFlashcards, selectedCount);
                this.removeRandomFlashcardCountModal();
            } else {
                alert(`Please enter a number between 1 and ${maxAllowed}`);
            }
        });
        
        document.getElementById('cancel-random-flashcards-btn').addEventListener('click', () => {
            this.removeRandomFlashcardCountModal();
        });
        
        // Close on overlay click
        document.querySelector('.question-count-overlay').addEventListener('click', () => {
            this.removeRandomFlashcardCountModal();
        });
        
        // Focus on input and select text
        const input = document.getElementById('random-flashcard-count-input');
        input.focus();
        input.select();
        
        // Allow Enter key to start flashcards
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('start-random-flashcards-btn').click();
            }
        });
    }

    removeRandomFlashcardCountModal() {
        const modal = document.querySelector('.question-count-modal');
        const overlay = document.querySelector('.question-count-overlay');
        if (modal) modal.remove();
        if (overlay) overlay.remove();
    }

    startRandomFlashcardsWithSelectedCount(allFlashcards, selectedCount) {
        // Convert to the format expected by the flashcards interface and shuffle
        const shuffledFlashcards = this.shuffleFlashcards([...allFlashcards]).slice(0, selectedCount);
        this.currentFlashcards = shuffledFlashcards.map(card => ({
            concept: card.front,
            description: card.back
        }));
        this.allFlashcards = [...this.currentFlashcards];
        this.currentFlashcardsStudyId = null; // No specific study ID since it's mixed content
        
        console.log(`Starting random flashcards with ${selectedCount} cards from saved content`);
        
        // Switch directly to flashcards interface and start
        this.switchToFlashcardsInterface();
        this.startFlashcards();
    }

    switchToQuizInterface() {
        // Hide all tabs first
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.style.display = 'none';
        });

        // Remove active class from all buttons
        document.querySelectorAll('.tab-buttons button').forEach(btn => {
            btn.classList.remove('active');
        });

        // Show quiz tab
        const quizTab = document.getElementById('quiz-tab');
        if (quizTab) {
            quizTab.style.display = 'block';
        }

        // Add active class to quiz tab button
        const quizButton = document.querySelector('[data-tab="quiz-tab"]');
        if (quizButton) {
            quizButton.classList.add('active');
        }

        // Skip the options and go directly to setup, which will be hidden by startQuiz()
        document.getElementById('quiz-options').classList.add('hidden');
        document.getElementById('quiz-setup').classList.remove('hidden');
        document.getElementById('quiz-interface').classList.add('hidden');
        document.getElementById('quiz-results').classList.add('hidden');
    }

    switchToFlashcardsInterface() {
        // Hide all tabs first
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.style.display = 'none';
        });

        // Remove active class from all buttons
        document.querySelectorAll('.tab-buttons button').forEach(btn => {
            btn.classList.remove('active');
        });

        // Show flashcards tab
        const flashcardsTab = document.getElementById('flashcards-tab');
        if (flashcardsTab) {
            flashcardsTab.style.display = 'block';
        }

        // Add active class to flashcards tab button
        const flashcardsButton = document.querySelector('[data-tab="flashcards-tab"]');
        if (flashcardsButton) {
            flashcardsButton.classList.add('active');
        }

        // Skip the options and go directly to setup, which will be hidden by startFlashcards()
        document.getElementById('flashcards-options').classList.add('hidden');
        document.getElementById('flashcards-setup').classList.remove('hidden');
        document.getElementById('flashcards-interface').classList.add('hidden');
        document.getElementById('flashcards-results').classList.add('hidden');
    }

    async deleteItem(itemId, type = 'item') {
        if (confirm('Are you sure you want to delete this study item?')) {
            try {
                // Check if itemId is numeric (database ID) or string (filename for backward compatibility)
                const endpoint = /^\d+$/.test(itemId) ? `/api/delete-study-item/${itemId}` : `/api/delete-study-item/${itemId}`;
                
                const response = await authFetch(endpoint, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    this.loadSavedItems();
                    
                    // Determine item type for display message
                    let itemType = 'item';
                    if (type.includes('quiz')) {
                        itemType = type.includes('individual') ? 'question' : 'quiz';
                    } else if (type.includes('flashcards')) {
                        itemType = type.includes('individual') ? 'flashcard' : 'flashcard set';
                    }
                    
                    alert(`${itemType.charAt(0).toUpperCase() + itemType.slice(1)} deleted successfully.`);
                } else {
                    alert('Error deleting study item.');
                }
            } catch (error) {
                console.error('Error deleting item:', error);
                alert('Error deleting study item.');
            }
        }
    }

    async deleteAllQuizzes() {
        const confirmed = confirm('Are you sure you want to delete ALL saved quizzes? This action cannot be undone.');
        if (!confirmed) return;

        try {
            const response = await authFetch('/api/delete-all-study-items/quiz', {
                method: 'DELETE'
            });
            
            if (response.ok) {
                alert('All quizzes have been deleted successfully.');
                this.loadSavedItems();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to delete quizzes');
            }
        } catch (error) {
            console.error('Error deleting all quizzes:', error);
            alert('Error deleting quizzes: ' + error.message);
        }
    }

    async deleteAllFlashcards() {
        const confirmed = confirm('Are you sure you want to delete ALL saved flashcards? This action cannot be undone.');
        if (!confirmed) return;

        try {
            const response = await authFetch('/api/delete-all-study-items/flashcards', {
                method: 'DELETE'
            });
            
            if (response.ok) {
                alert('All flashcards have been deleted successfully.');
                this.loadSavedItems();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to delete flashcards');
            }
        } catch (error) {
            console.error('Error deleting all flashcards:', error);
            alert('Error deleting flashcards: ' + error.message);
        }
    }

    resetState() {
        this.resetQuizState();
        this.resetFlashcardsState();
    }

    resetQuizState(resetAccumulatedScore = true) {
        this.currentQuiz = null;
        this.currentQuestionIndex = 0;
        this.userAnswers = [];
        this.answeredQuestions = [];
        if (resetAccumulatedScore) {
            this.quizScore = { correct: 0, total: 0 };
        }
        this.isQuizFinished = false;
        this.allQuizQuestions = [];
        this.isGeneratingMore = false;
        this.currentQuizStudyId = null; // Reset study ID when starting fresh
        
        document.getElementById('quiz-interface').classList.add('hidden');
        document.getElementById('quiz-results').classList.add('hidden');
        document.getElementById('quiz-options').classList.remove('hidden');
        document.getElementById('quiz-setup').classList.add('hidden');
        
        // Reset button text
        const startBtn = document.getElementById('start-quiz-btn');
        if (startBtn) {
            startBtn.textContent = 'Generate Quiz';
        }
    }

    resetFlashcardsState() {
        this.currentFlashcards = null;
        this.currentFlashcardIndex = 0;
        this.allFlashcards = [];
        this.isGeneratingMore = false;
        this.globalShowAnswers = false;
        this.currentCardShowAnswer = false;
        this.currentFlashcardsStudyId = null; // Reset study ID when starting fresh
        
        document.getElementById('flashcards-interface').classList.add('hidden');
        document.getElementById('flashcards-results').classList.add('hidden');
        document.getElementById('flashcards-options').classList.remove('hidden');
        document.getElementById('flashcards-setup').classList.add('hidden');
        
        // Reset button text
        const startBtn = document.getElementById('start-flashcards-btn');
        if (startBtn) {
            startBtn.textContent = 'Generate Flashcards';
        }
    }

    // Utility functions for randomization
    shuffleArray(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }

    shuffleQuiz(questions) {
        // Shuffle the order of questions
        const shuffledQuestions = this.shuffleArray(questions);
        
        // Shuffle the answers within each question while keeping track of correct answer
        return shuffledQuestions.map(question => {
            const originalAnswers = [...question.answers];
            const originalCorrectIndex = question.correct_answer !== undefined ? question.correct_answer : question.correct;
            const originalCorrectAnswer = originalAnswers[originalCorrectIndex];
            
            // Create array of answer objects with their original indices
            const answerObjects = originalAnswers.map((answer, index) => ({
                text: answer,
                wasCorrect: index === originalCorrectIndex
            }));
            
            // Shuffle the answer objects
            const shuffledAnswerObjects = this.shuffleArray(answerObjects);
            
            // Extract shuffled answers and find new correct index
            const shuffledAnswers = shuffledAnswerObjects.map(obj => obj.text);
            const newCorrectIndex = shuffledAnswerObjects.findIndex(obj => obj.wasCorrect);
            
            return {
                ...question,
                answers: shuffledAnswers,
                correct_answer: newCorrectIndex,
                correct: newCorrectIndex // Support both formats
            };
        });
    }

    shuffleFlashcards(flashcards) {
        return this.shuffleArray(flashcards);
    }

    // New functions for study options interface
    showQuizSetup() {
        document.getElementById('quiz-options').classList.add('hidden');
        document.getElementById('quiz-setup').classList.remove('hidden');
        
        // Update button text to show current chunk info
        this.updateQuizButtonText();
    }

    showFlashcardsSetup() {
        document.getElementById('flashcards-options').classList.add('hidden');
        document.getElementById('flashcards-setup').classList.remove('hidden');
        
        // Update button text to show current chunk info
        this.updateFlashcardsButtonText();
    }

    updateQuizButtonText() {
        const startBtn = document.getElementById('start-quiz-btn');
        if (startBtn && this.noteChunks.length > 1) {
            const chunkIndex = this.currentQuizChunkIndex >= this.noteChunks.length ? 1 : this.currentQuizChunkIndex + 1;
            const chunkInfo = `(Chunk ${chunkIndex} of ${this.noteChunks.length})`;
            startBtn.textContent = `Generate Quiz ${chunkInfo}`;
        }
    }

    updateFlashcardsButtonText() {
        const startBtn = document.getElementById('start-flashcards-btn');
        if (startBtn && this.noteChunks.length > 1) {
            const chunkIndex = this.currentFlashcardsChunkIndex >= this.noteChunks.length ? 1 : this.currentFlashcardsChunkIndex + 1;
            const chunkInfo = `(Chunk ${chunkIndex} of ${this.noteChunks.length})`;
            startBtn.textContent = `Generate Flashcards ${chunkInfo}`;
        }
    }

    async startRandomQuiz() {
        try {
            // Show loading
            const startBtn = document.getElementById('study-saved-quiz-btn');
            const originalText = startBtn.textContent;
            startBtn.textContent = 'Loading Quiz Options...';
            startBtn.disabled = true;

            // Get random questions from all saved quizzes
            const response = await authFetch('/api/get-random-study-content/quiz');
            
            if (!response.ok) {
                if (response.status === 404) {
                    alert('No saved quizzes found. Please generate and save some quizzes first.');
                    return;
                }
                throw new Error('Failed to load random quiz');
            }

            const data = await response.json();
            
            if (data.questions && data.questions.length > 0) {
                // Show question count selector modal before starting
                this.showRandomQuizCountSelector(data.questions);
            } else {
                alert('No questions found in saved quizzes.');
            }
            
        } catch (error) {
            console.error('Error starting random quiz:', error);
            alert('Error loading random quiz: ' + error.message);
        } finally {
            const startBtn = document.getElementById('study-saved-quiz-btn');
            startBtn.textContent = 'Study Saved Quizzes';
            startBtn.disabled = false;
        }
    }

    async startRandomFlashcards() {
        try {
            // Show loading
            const startBtn = document.getElementById('study-saved-flashcards-btn');
            const originalText = startBtn.textContent;
            startBtn.textContent = 'Loading Flashcard Options...';
            startBtn.disabled = true;

            // Get random flashcards from all saved sets
            const response = await authFetch('/api/get-random-study-content/flashcards');
            
            if (!response.ok) {
                if (response.status === 404) {
                    alert('No saved flashcards found. Please generate and save some flashcards first.');
                    return;
                }
                throw new Error('Failed to load random flashcards');
            }

            const data = await response.json();
            
            if (data.flashcards && data.flashcards.length > 0) {
                // Show flashcard count selector modal before starting
                this.showRandomFlashcardCountSelector(data.flashcards);
            } else {
                alert('No flashcards found in saved sets.');
            }
            
        } catch (error) {
            console.error('Error starting random flashcards:', error);
            alert('Error loading random flashcards: ' + error.message);
        } finally {
            const startBtn = document.getElementById('study-saved-flashcards-btn');
            startBtn.textContent = 'Study Saved Flashcards';
            startBtn.disabled = false;
        }
    }

    async showSavedQuizzes() {
        // Load saved items and filter quizzes
        await this.loadSavedItems();
        this.switchTab('saved-tab');
    }

    async showSavedFlashcards() {
        // Load saved items and filter flashcards
        await this.loadSavedItems();
        this.switchTab('saved-tab');
    }

    // Override switchTab to reset to options view
    switchTab(tabId) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.style.display = 'none';
        });

        // Remove active class from all buttons - using the correct classes
        document.querySelectorAll('[data-tab]').forEach(button => {
            button.classList.remove('btn--primary');
            button.classList.add('btn--outline');
        });

        // Show selected tab
        const selectedTab = document.getElementById(tabId);
        if (selectedTab) {
            selectedTab.style.display = 'block';
        }

        // Add active class to clicked button - using the correct classes
        const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
        if (activeButton) {
            activeButton.classList.remove('btn--outline');
            activeButton.classList.add('btn--primary');
        }

        // Reset to options view when switching to quiz or flashcards tabs
        if (tabId === 'quiz-tab') {
            document.getElementById('quiz-options').classList.remove('hidden');
            document.getElementById('quiz-setup').classList.add('hidden');
            document.getElementById('quiz-interface').classList.add('hidden');
            document.getElementById('quiz-results').classList.add('hidden');
        } else if (tabId === 'flashcards-tab') {
            document.getElementById('flashcards-options').classList.remove('hidden');
            document.getElementById('flashcards-setup').classList.add('hidden');
            document.getElementById('flashcards-interface').classList.add('hidden');
            document.getElementById('flashcards-results').classList.add('hidden');
        } else if (tabId === 'saved-tab' || tabId === 'saved-items') {
            // Reload saved items from server when switching to saved items tab
            this.loadSavedItems();
        }
    }
}

// Initialize study manager
const studyManager = new StudyManager();

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
