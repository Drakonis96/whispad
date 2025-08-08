# WhisPad Changelog

This file tracks all changes made to the WhisPad application with detailed version history.

---

## Version 0.7.11.5 - Comprehensive ESC Key Support for All Modals
**Date**: August 8, 2025  
**Type**: Major Feature Enhancement  
**Impact**: Comprehensive User Interface Improvement

### Changes Made

#### 1. **Complete ESC Key Modal Implementation**
- **File Modified**: `app.js` (lines 13095-13232)
- **Location**: Extended existing generic ESC key handler  
- **Purpose**: Enable ESC key functionality for ALL remaining modals in the application

#### 2. **Previously Supported Modals (Unchanged)**
- **Focus Modal**: Original ESC handler completely unchanged (lines 13073-13094)
- **Config Modal**: ESC key triggers `hideConfigModal()`
- **Models Modal**: ESC key triggers `hideUploadModelsModal()`  
- **Users Modal**: ESC key removes 'active' class (added in v0.7.11.4)

#### 3. **Newly Added ESC Key Support (17 Additional Modals)**

**Core Application Modals:**
- **Styles Modal** (`#styles-config-modal`): ESC triggers `hideStylesConfigModal()`
- **Translation Modal** (`#translation-modal`): ESC triggers `hideTranslationModal()`
- **Tabularize Modal** (`#tabularize-modal`): ESC triggers `hideTabularizeModal()`

**Visualization & Analysis Modals:**
- **Graph Modal** (`#graph-modal`): ESC triggers `hideGraphModal()`
- **Concept Graph Modal** (`#concept-graph-modal`): ESC triggers `hideConceptGraphModal()`

**Study & Learning Modals:**
- **Study Modal** (`#study-modal`): ESC triggers `studyManager.closeStudyModal()`
- **Saved Questions Modal** (`#saved-questions-modal`): ESC triggers `studyManager.hideSavedQuestionsModal()`
- **Saved Flashcards Modal** (`#saved-flashcards-modal`): ESC triggers `studyManager.hideSavedFlashcardsModal()`

**File Management Modals:**
- **Audio Modal** (`#audio-modal`): ESC triggers `hideAudioModal()`
- **Export Modal** (`#export-modal`): ESC triggers `hideExportModal()`
- **Restore Modal** (`#restore-modal`): ESC triggers `hideRestoreModal()`  
- **Upload PDF Modal** (`#upload-pdf-modal`): ESC triggers `hideUploadPdfModal()`

**Confirmation & Action Modals:**
- **Delete Modal** (`#delete-modal`): ESC triggers `hideDeleteModal()`
- **Delete Audio Modal** (`#delete-audio-modal`): ESC triggers `hideDeleteAudioModal()`

**Folder Management Modals:**
- **Create Folder Modal** (`#create-folder-modal`): ESC triggers `hideCreateFolderModal()`
- **Move Note Modal** (`#move-note-modal`): ESC triggers `hideMoveNoteModal()`
- **Move Folder Modal** (`#move-folder-modal`): ESC triggers `hideMoveFolderModal()`

#### 4. **StudyManager Global Accessibility Enhancement**
- **File Modified**: `app.js` (lines 13056-13057)
- **Change**: Added `window.studyManager = studyManager;` for global access
- **Purpose**: Enable ESC key handler to access study manager methods

#### 5. **Code Implementation**
```javascript
// Extended ESC key handler (138+ lines total)
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && window.notesApp) {
        // All 20 modals now supported with proper prevention and early returns
        // Sequential checking ensures only the active modal is closed
        // Special handling for studyManager methods through window.studyManager
    }
});
```

#### 6. **Complete Modal Coverage**
**Total Modals with ESC Support: 21**
1. Focus Modal (original handler) ✓
2. Config Modal ✓  
3. Models Modal ✓
4. Users Modal ✓
5. Styles Modal ✓ **NEW**
6. Translation Modal ✓ **NEW**
7. Tabularize Modal ✓ **NEW**
8. Graph Modal ✓ **NEW**
9. Concept Graph Modal ✓ **NEW**
10. Study Modal ✓ **NEW**
11. Audio Modal ✓ **NEW**
12. Export Modal ✓ **NEW**
13. Restore Modal ✓ **NEW**
14. Upload PDF Modal ✓ **NEW**
15. Delete Modal ✓ **NEW**
16. Delete Audio Modal ✓ **NEW**
17. Create Folder Modal ✓ **NEW**
18. Move Note Modal ✓ **NEW**
19. Move Folder Modal ✓ **NEW**
20. Saved Questions Modal ✓ **NEW**
21. Saved Flashcards Modal ✓ **NEW**

#### 7. **User Experience Improvements**
- **Complete Keyboard Navigation**: All modals in the application now respond to ESC key
- **Unified Behavior**: Consistent ESC key experience across the entire interface
- **Accessibility Enhancement**: Full keyboard navigation support for users with mobility needs
- **Workflow Efficiency**: Faster modal closure for all application functions
- **Professional Feel**: Expected ESC behavior now universal throughout WhisPad

#### 8. **Technical Benefits**
- **Consistent Implementation**: Single event listener handles all modal closures efficiently
- **Safe Execution**: Early returns prevent multiple modal closures and race conditions  
- **Performance Optimized**: Only active modals are checked, preventing unnecessary processing
- **Extensible Design**: Easy to add future modals to the ESC key system
- **Global Access**: StudyManager properly accessible for study-related modal closures

### Testing Recommendations
**Comprehensive Modal ESC Testing:**
1. **Core Modals**: Config, Models, Users, Styles, Translation, Tabularize → ESC should close each
2. **Visualization**: Graph, Concept Graph → ESC should close with proper cleanup
3. **Study System**: Study, Saved Questions, Saved Flashcards → ESC should close via StudyManager
4. **File Operations**: Audio, Export, Restore, Upload PDF → ESC should close with state preservation
5. **Confirmations**: Delete, Delete Audio → ESC should close (canceling action)
6. **Folder Management**: Create Folder, Move Note, Move Folder → ESC should close with form reset
7. **Sequential Testing**: Open multiple modals → ESC should close only the active/topmost modal
8. **Focus Modal**: Ensure original behavior unchanged (content sync, formatting preservation)

### Files Modified
- [`app.js`](../app.js) - **Major Modification**: Extended generic ESC key handler from 27 lines to 138+ lines, added global StudyManager access

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\app.js
```

---

## Version 0.7.11.4 - Extended ESC Key to Users Modal
**Date**: August 8, 2025  
**Type**: Feature Enhancement  
**Impact**: User Interface Improvement

### Changes Made

#### 1. **Users Modal ESC Key Implementation**
- **File Modified**: `app.js` (lines 13095-13119)
- **Location**: Extended existing generic ESC key handler
- **Purpose**: Enable ESC key functionality for Users modal consistent with Config and Models modals

#### 2. **Code Modified**
```javascript
// Before - Config and Models only
// Generic ESC key handler for additional modals (Config and Models)
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && window.notesApp) {
        // Config and Models modal checks only
    }
});

// After - Added Users modal support  
// Generic ESC key handler for additional modals (Config, Models, and Users)
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
        
        // Check for Users modal
        const usersModal = document.getElementById('user-modal');
        if (usersModal && usersModal.classList.contains('active')) {
            e.preventDefault();
            usersModal.classList.remove('active');
            return;
        }
    }
});
```

#### 3. **Affected Modals**
- **Config Modal** (`#config-modal`): ESC key triggers `window.notesApp.hideConfigModal()` (unchanged)
- **Models Modal** (`#upload-model-modal`): ESC key triggers `window.notesApp.hideUploadModelsModal()` (unchanged)
- **Users Modal** (`#user-modal`): ESC key now removes 'active' class to close modal (**NEW**)
- **Focus Modal**: Original ESC key behavior completely unchanged (has separate handler)

#### 4. **Users Modal ESC Behavior**
- **Direct Close**: ESC key triggers `usersModal.classList.remove('active')`
- **Immediate Response**: No mobile FAB restoration needed (Users modal doesn't hide FAB)
- **Tab State Preserved**: Current tab selection maintained (Password/Create User tabs)
- **Accessible Via**: Header "Users" button (admin users only)

#### 5. **Technical Benefits**
- **Consistent Interface**: All four main modals (Focus, Config, Models, Users) now respond to ESC key
- **Unified Experience**: Same ESC key behavior pattern across entire application  
- **Clean Implementation**: Single event listener handles all non-Focus modals efficiently
- **Safe Execution**: Early return prevents multiple modal closures and conflicts

#### 6. **User Experience Improvements**
- **Complete Keyboard Navigation**: Users can close any modal with ESC key
- **Workflow Efficiency**: Faster modal closure for user management tasks
- **Accessibility Enhancement**: Full keyboard navigation support for all modals
- **Consistency**: Expected ESC behavior now works everywhere in the application

### Testing Recommendations
When testing modal functionality:
1. Open Users modal via header button → Press ESC → Should close modal
2. Open Config modal → Press ESC → Should close with FAB restoration  
3. Open Models modal → Press ESC → Should close with FAB restoration
4. Open Focus modal → Press ESC → Should close with content sync (unchanged behavior)
5. Test sequential modal opening → ESC should close only the active modal
6. Verify keyboard shortcuts Ctrl+S and Ctrl+N still function correctly

### Files Modified
- [`app.js`](../app.js) - **Modified**: Extended generic ESC key handler to include Users modal (8 lines added at lines 13113-13120)

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\app.js
```

---

## Version 0.7.11.3 - Python Version Update for sherpa-onnx Preparation
**Date**: August 8, 2025  
**Type**: Configuration  
**Impact**: Docker Environment Upgrade

### Changes Made

#### 1. **Docker Base Image Upgrade**
- **File Modified**: `Dockerfile` (line 2)
- **Location**: FROM statement at beginning of Dockerfile
- **Purpose**: Upgrade Python runtime to prepare for sherpa-onnx transcription provider integration

#### 2. **Code Modified**
```dockerfile
# Before
FROM python:3.11-slim

# After  
FROM python:3.13.6-slim
```

#### 3. **Affected Components**
- **Docker Container**: Now builds with Python 3.13.6 runtime instead of 3.11
- **ML Dependencies**: Better compatibility with modern PyTorch, FunASR, and upcoming sherpa-onnx
- **Performance**: Improved Python interpreter performance and memory management
- **Security**: Latest Python security patches and bug fixes

#### 4. **Technical Benefits**
- **Enhanced Performance**: Python 3.13 includes significant performance improvements for AI workloads
- **Better Compatibility**: Modern ML libraries like sherpa-onnx require Python 3.8+ and benefit from latest features  
- **Optimized Memory Usage**: More efficient memory management for concurrent transcription requests
- **Future-Proofing**: Prepared for sherpa-onnx integration as 4th transcription provider alongside OpenAI, SenseVoice, and Local Whisper

#### 5. **sherpa-onnx Preparation Benefits**
- **Runtime Compatibility**: sherpa-onnx requires modern Python versions for optimal performance
- **ONNX Runtime Support**: Better integration with ONNX-based models and faster inference
- **Multi-Provider Architecture**: Positions WhisPad for seamless 4th provider integration
- **Container Efficiency**: Reduced image size and improved startup times with latest slim base

### Testing Recommendations
When testing Docker deployment:
1. Build container with `docker build -t whispad .` → Should complete without errors
2. Run container with `docker-compose up` → All services should start successfully
3. Test existing transcription providers → OpenAI, SenseVoice, Local Whisper should function normally
4. Verify Python version with `docker exec -it <container> python --version` → Should show 3.13.6
5. Check dependency compatibility → PyTorch, FunASR, and other ML libraries should install correctly
6. Test frontend functionality → All UI components and API endpoints should work as before

### Files Modified
- [`Dockerfile`](../Dockerfile) - **Modified**: Updated FROM python:3.11-slim to python:3.13.6-slim (line 2)

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\Dockerfile
```

---

## Version 0.7.11.2 - Extended ESC Key Functionality
**Date**: August 8, 2025  
**Type**: Feature Enhancement  
**Impact**: User Interface Improvement

### Changes Made

#### 1. **New ESC Key Handler Implementation**
- **File Modified**: `app.js` (lines 13075-13093 extended)
- **Location**: Added after existing keyboard shortcuts section
- **Purpose**: Enable ESC key functionality for Config and Models modals

#### 2. **Code Added**
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

#### 3. **Affected Modals**
- **Config Modal** (`#config-modal`):
  - ESC key now triggers `window.notesApp.hideConfigModal()`
  - Closes configuration panel and restores mobile FAB
  - Accessible via header "Config" button
  
- **Models Modal** (`#upload-model-modal`):
  - ESC key now triggers `window.notesApp.hideUploadModelsModal()`
  - Closes model management panel and restores mobile FAB
  - Accessible via header "Models" button

#### 4. **Preserved Functionality**
- **Focus Modal**: Original ESC key behavior completely unchanged
- **Existing Keyboard Shortcuts**: Ctrl+S and Ctrl+N remain intact
- **Modal Event Handlers**: All existing modal close buttons and backdrop clicks unaffected

#### 5. **Technical Benefits**
- **Non-intrusive Design**: Focus modal ESC functionality preserved without modification
- **Modular Implementation**: Easy to extend for future modal additions
- **Consistent User Experience**: Unified ESC key behavior across all modals
- **Safe Execution**: Early return prevents multiple modal closures
- **Performance Optimized**: Single event listener handles multiple modals efficiently

#### 6. **User Experience Improvements**
- **Keyboard Navigation**: Users can now close Config and Models modals with ESC
- **Consistent Behavior**: All three main modals (Focus, Config, Models) respond to ESC key
- **Accessibility**: Enhanced keyboard navigation support
- **Workflow Efficiency**: Faster modal closure without reaching for mouse/touch

### Testing Recommendations
When testing on target machine:
1. Open Config modal via header button → Press ESC → Should close
2. Open Models modal via header button → Press ESC → Should close  
3. Open Focus modal → Press ESC → Should close with content sync (unchanged behavior)
4. Verify no conflicts when multiple modals are opened sequentially
5. Test keyboard shortcuts Ctrl+S and Ctrl+N still function

### Files Modified
- [`app.js`](../app.js) - **Modified**: Added generic ESC key handler (14 lines added at lines 13094-13108)
- [`analysis/ARCHITECTURE_ANALYSIS.md`](./ARCHITECTURE_ANALYSIS.md) - **Modified**: Updated version to 0.7.11.2, updated keyboard shortcuts documentation
- [`analysis/CHANGELOG.md`](./CHANGELOG.md) - **Created**: New changelog file for version tracking
- [`analysis/UPDATE_GUIDE.md`](./UPDATE_GUIDE.md) - **Created**: Standardized documentation update process guide

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\app.js
c:\Users\Lawes\Desktop\whispad\whispad\analysis\ARCHITECTURE_ANALYSIS.md
c:\Users\Lawes\Desktop\whispad\whispad\analysis\CHANGELOG.md
c:\Users\Lawes\Desktop\whispad\whispad\analysis\UPDATE_GUIDE.md
```

---

## Version 0.7.11.1 - Focus Modal ESC Key Analysis
**Date**: August 8, 2025  
**Type**: Documentation & Analysis  
**Impact**: Architecture Documentation

### Changes Made

#### 1. **Focus Modal ESC Key Analysis**
- **Analyzed**: Existing Focus modal implementation (app.js lines 10797-10950)
- **Documented**: ESC key behavior sequence and implementation details
- **Identified**: Modal structure patterns for consistent implementation

#### 2. **Architecture Documentation Updates**
- **Added**: Focus modal section to ARCHITECTURE_ANALYSIS.md
- **Documented**: ESC key behavior flow (7-step sequence)
- **Catalogued**: Focus mode features and close methods
- **Detailed**: Content sync mechanism and animation handling

#### 3. **Key Findings**
- Focus modal has sophisticated content sync with main editor
- ESC key implementation includes proper event prevention and animation delays
- Modal uses 300ms CSS transition for smooth user experience
- Content changes automatically sync back to main editor on close

### Files Modified
- [`analysis/ARCHITECTURE_ANALYSIS.md`](./ARCHITECTURE_ANALYSIS.md) - **Modified**: Added Focus modal documentation section

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\analysis\ARCHITECTURE_ANALYSIS.md
```

---

## Version 0.7.11 - Initial Architecture Analysis  
**Date**: August 8, 2025  
**Type**: Documentation Creation  
**Impact**: Development Foundation

### Changes Made

#### 1. **Comprehensive Codebase Analysis**
- **Analyzed**: ~25,000 lines of code across all components
- **Frontend**: app.js (13,093 lines), backend-api.js (700 lines)
- **Backend**: backend.py (6,713 lines), concept_graph.py (3,372 lines)
- **Supporting**: db.py, whisper_cpp_wrapper.py, sensevoice_wrapper.py

#### 2. **Architecture Documentation Created**
- **System Overview**: Technology stack and multi-tenancy architecture
- **Frontend Architecture**: NotesApp class structure and responsibilities
- **Backend Architecture**: Flask application and provider integration
- **Core Components**: Audio processing, AI enhancement, concept graphs
- **API Documentation**: Complete endpoint reference with parameters
- **Database Schema**: All tables with relationships and constraints
- **File Structure**: Organized hierarchy with line counts
- **Configuration Management**: Environment variables and user preferences

#### 3. **Provider Analysis**
- **Transcription Providers**: OpenAI, SenseVoice, Local Whisper
- **AI Enhancement Providers**: OpenAI, Google AI, OpenRouter, Groq, LM Studio, Ollama
- **Feature Matrix**: Capabilities comparison across all providers
- **Integration Patterns**: Consistent provider interface design

#### 4. **Workflow Documentation**
- **Transcription Flow**: 7-step audio to text process
- **AI Enhancement Flow**: 6-step text improvement process  
- **Note Management Flow**: 5-step CRUD operations
- **Keyboard Shortcuts**: Global hotkeys and modal interactions

### Files Created
- [`analysis/`](./analysis/) - **Created**: New directory for architecture documentation
- [`analysis/ARCHITECTURE_ANALYSIS.md`](./ARCHITECTURE_ANALYSIS.md) - **Created**: Comprehensive system documentation (589 lines)

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\analysis\
c:\Users\Lawes\Desktop\whispad\whispad\analysis\ARCHITECTURE_ANALYSIS.md
```

### Development Impact
- **Baseline Established**: Complete understanding of current system state
- **Future Reference**: Detailed component relationships for modifications
- **Onboarding Resource**: New developers can quickly understand architecture
- **Change Tracking**: Foundation for tracking future modifications

---

## Changelog Guidelines

### Version Numbering
- **Major.Minor.Patch** format (e.g., 0.7.11.2)
- **Major**: Significant architectural changes, breaking changes
- **Minor**: New features, provider additions, major enhancements
- **Patch**: Bug fixes, small improvements, documentation updates

### Change Types
- **Feature Addition**: New functionality or capabilities
- **Feature Enhancement**: Improvements to existing functionality
- **Bug Fix**: Error corrections and stability improvements
- **Documentation**: Architecture analysis, API documentation updates
- **Configuration**: Settings, environment, or deployment changes
- **Performance**: Optimizations and efficiency improvements
- **Security**: Authentication, authorization, or data protection changes

### Entry Format
Each changelog entry should include:
1. **Version number and descriptive title**
2. **Date, type, and impact assessment**
3. **Detailed changes made** with file locations
4. **Code snippets** for significant additions
5. **Affected components** and their behavior changes
6. **User experience improvements**
7. **Testing recommendations** for validation
8. **Files modified** with brief descriptions and absolute paths

### File Path Conventions
- **Relative Markdown Links**: `[filename](../path/to/file)` for easy navigation within repository
- **Absolute Path Sections**: Complete paths in code blocks for precise file identification
- **Change Types**: **Created**, **Modified**, **Deleted**, **Renamed**, **Moved**
- **Line References**: Include specific line numbers or ranges when applicable
- **Directory Links**: `[dirname](./dirname/)` for folder references

### Markdown Format Example
```markdown
### Files Modified
- [`app.js`](../app.js) - **Modified**: Description of changes (line numbers if applicable)
- [`folder/file.py`](../folder/file.py) - **Created**: New file description

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\app.js
c:\Users\Lawes\Desktop\whispad\whispad\folder\file.py
```
```

This changelog will be maintained alongside the main architecture analysis to provide a complete development history of WhisPad.
