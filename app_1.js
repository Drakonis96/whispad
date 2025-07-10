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
        
        this.init();
    }
    
    async init() {
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
    
    startRecording() {
        this.isRecording = true;
        
        const recordBtn = document.getElementById('record-btn');
        const recordIcon = document.getElementById('record-icon');
        const recordText = document.getElementById('record-text');
        const recordingStatus = document.getElementById('recording-status');
        const recordingIndicator = document.getElementById('recording-indicator');
        
        recordBtn.classList.add('btn--error');
        recordIcon.className = 'fas fa-stop';
        recordText.textContent = 'Detener';
        recordingStatus.querySelector('.status-text').textContent = 'Grabando...';
        recordingIndicator.classList.add('active');
        
        // Simular transcripción después de 3-5 segundos
        const duration = 3000 + Math.random() * 2000;
        setTimeout(() => {
            if (this.isRecording) {
                this.stopRecording();
            }
        }, duration);
    }
    
    stopRecording() {
        this.isRecording = false;
        
        const recordBtn = document.getElementById('record-btn');
        const recordIcon = document.getElementById('record-icon');
        const recordText = document.getElementById('record-text');
        const recordingStatus = document.getElementById('recording-status');
        const recordingIndicator = document.getElementById('recording-indicator');
        
        recordBtn.classList.remove('btn--error');
        recordIcon.className = 'fas fa-microphone';
        recordText.textContent = 'Record';
        recordingStatus.querySelector('.status-text').textContent = 'Transcribing...';
        recordingIndicator.classList.remove('active');
        
        // Simular procesamiento
        setTimeout(() => {
            this.insertTranscription();
            recordingStatus.querySelector('.status-text').textContent = 'Ready to record';
        }, 1500);
    }
    
    insertTranscription() {
        const transcription = ejemplosTranscripcion[Math.floor(Math.random() * ejemplosTranscripcion.length)];
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
        
        this.showNotification('Transcripción completada');
    }
    
    // Mejora con IA
    improveText(action) {
        // Verificar si hay texto seleccionado
        if (!this.selectedText || !this.selectedRange) {
            this.showNotification('Please select text to improve with AI', 'warning');
            return;
        }
        
        this.showProcessingOverlay(`Improving text with AI...`);
        
        // Simular procesamiento de IA
        setTimeout(() => {
            const improvedText = this.applyAIImprovement(this.selectedText, action);
            
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
            
            this.hideProcessingOverlay();
            this.showNotification(`Texto mejorado: ${configuracionMejoras[action].nombre}`);
            this.handleEditorChange();
        }, 2000);
    }
    
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
        }
        
        this.updateFormatButtons();
        this.handleEditorChange();
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
            }
            
            btn.classList.toggle('active', isActive);
        });
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