# WhisPad Documentation Update Guide

**Purpose**: Standardized process for maintaining documentation when making changes to WhisPad  
**Location**: `analysis/UPDATE_GUIDE.md`  
**Usage**: Follow this guide every time code changes are made to ensure consistent documentation

---

## 📋 Standard Update Process

### Step 1: Version Number Assignment
Determine the appropriate version number based on change type:

- **Major** (X.0.0): Breaking changes, complete rewrites, architectural overhauls
- **Minor** (0.X.0): New features, new providers, significant enhancements  
- **Patch** (0.0.X): Bug fixes, small improvements, documentation updates

**Current Version**: 0.7.11.2 *(Update this when incrementing)*

### Step 2: Update CHANGELOG.md
Add new entry at the top using this exact template:

```markdown
## Version X.X.X - [Descriptive Title]
**Date**: [Current Date]  
**Type**: [Feature Addition|Feature Enhancement|Bug Fix|Documentation|Configuration|Performance|Security]  
**Impact**: [Brief impact description]

### Changes Made

#### 1. **[Change Category 1]**
- **File Modified**: `filename` (specific lines if applicable)
- **Location**: Where in the file the change was made
- **Purpose**: Why this change was made

#### 2. **Code Added/Modified** *(Include for significant code changes)*
```[language]
[Code snippet with context]
```

#### 3. **Affected Components**
- **Component Name**: Description of how it's affected
- **Another Component**: Description of changes

#### 4. **Technical Benefits**
- **Benefit 1**: Explanation
- **Benefit 2**: Explanation

#### 5. **User Experience Improvements**
- **Improvement 1**: How users benefit
- **Improvement 2**: Additional user benefits

### Testing Recommendations
When testing on target machine:
1. Test step 1
2. Test step 2
3. Verify no regressions

### Files Modified
- [`filename`](../path/to/file) - **[Created|Modified|Deleted]**: Brief description (line numbers if applicable)
- [`another-file`](../path/to/another-file) - **[Action]**: Description

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\filename
c:\Users\Lawes\Desktop\whispad\whispad\path\to\another-file
```

---
```

### Step 3: Update ARCHITECTURE_ANALYSIS.md (If Needed)
Only update this file if there are **structural/architectural changes**:

1. **Update version number** in header:
   ```markdown
   **Version**: X.X.X
   ```

2. **Add/modify relevant sections** based on changes:
   - System Overview (for major architectural changes)
   - Frontend/Backend Architecture (for structural changes)
   - Core Components (for new components or major modifications)
   - API Endpoints (for new endpoints or significant changes)
   - Database Schema (for schema changes)
   - File Structure (for new major files or directory changes)
   - Configuration Management (for new config options)

3. **Keep Change Log section minimal** - just reference the CHANGELOG.md:
   ```markdown
   ## Change Log
   
   **Current Version**: X.X.X  
   **Last Architecture Update**: [Date]
   
   For detailed change history, version updates, and modification tracking, see [`CHANGELOG.md`](./CHANGELOG.md).
   ```

### Step 4: File Naming and Organization Standards

#### File Naming Convention
- **CHANGELOG.md**: Version history and detailed change tracking
- **ARCHITECTURE_ANALYSIS.md**: Current system architecture and structure
- **UPDATE_GUIDE.md**: This guide file (process documentation)

#### Absolute Path Format (Windows)
Always use this format in changelog:
```
c:\Users\Lawes\Desktop\whispad\whispad\[filename]
c:\Users\Lawes\Desktop\whispad\whispad\[folder]\[filename]
```

#### Relative Path Format (Markdown Links)
For clickable navigation:
```markdown
[filename](../filename)
[folder/file](../folder/file)
[analysis file](./analysis-file.md)
```

---

## 🎯 Quick Reference Commands

When instructed to update documentation, follow these exact steps:

### Command: "Update documentation for [change description]"
**Your Response Process**:

1. **Ask for version type** if not specified:
   - "Is this a major, minor, or patch update?"

2. **Determine new version number**:
   - Current: 0.7.11.2
   - Next: 0.7.11.3 (patch) or 0.7.12.0 (minor) or 0.8.0.0 (major)

3. **Create CHANGELOG.md entry**:
   - Use the template above
   - Include all modified files with absolute paths
   - Add code snippets for significant changes
   - Include testing recommendations

4. **Update ARCHITECTURE_ANALYSIS.md if needed**:
   - Only for architectural/structural changes
   - Update version number in header
   - Modify relevant sections
   - Keep changelog section minimal

5. **Confirm completion**:
   - List all files updated
   - Provide summary of changes made
   - Mention version number assigned

---

## 📝 Template Snippets

### CHANGELOG.md Entry Template
```markdown
## Version X.X.X - [Title]
**Date**: August X, 2025  
**Type**: [Type]  
**Impact**: [Impact]

### Changes Made

#### 1. **[Category]**
- **File Modified**: `filename` (lines X-Y)
- **Purpose**: [Purpose]

### Files Modified
- [`filename`](../filename) - **Modified**: [Description] (lines X-Y)

#### File Paths (Absolute)
```
c:\Users\Lawes\Desktop\whispad\whispad\filename
```

---
```

### Architecture Analysis Version Update
```markdown
**Version**: X.X.X
```

### File Status Indicators
- **Created**: New file
- **Modified**: Existing file changed
- **Deleted**: File removed
- **Renamed**: File name changed
- **Moved**: File location changed

---

## 🚨 Important Rules

### Always Do
✅ Update version number in both files when making changes  
✅ Include absolute file paths in changelog  
✅ Add testing recommendations for functionality changes  
✅ Use consistent markdown formatting  
✅ Include line numbers for code changes  
✅ Add code snippets for significant changes  
✅ Link files with relative paths for navigation  

### Never Do
❌ Skip version number updates  
❌ Forget to include absolute paths  
❌ Make architecture changes without documentation  
❌ Use inconsistent formatting  
❌ Omit testing instructions for new features  
❌ Leave broken relative links  

---

## 🔄 Maintenance Schedule

### When to Update Documentation
- **Every code change**: Update CHANGELOG.md
- **Structural changes**: Update ARCHITECTURE_ANALYSIS.md
- **New features**: Add detailed documentation
- **Bug fixes**: Brief changelog entry
- **Configuration changes**: Update both files if needed

### Version Control Integration
This documentation system works alongside git commits:
1. Make code changes
2. Update documentation (following this guide)
3. Commit both code and documentation together
4. Tag releases with version numbers

---

## 📞 Usage Instructions

**When you receive update instructions**, follow this process:

1. **Identify change type** from user description
2. **Assign appropriate version number**
3. **Follow Step 2** (CHANGELOG.md update)
4. **Follow Step 3** if architectural changes exist
5. **Confirm all files updated with version numbers**
6. **Provide summary** of documentation changes made

**Example User Instruction**:
> "Update documentation - I added a new AI provider called 'CustomAI' with streaming support"

**Your Response**:
1. Identify as minor version update (new feature)
2. Version 0.7.11.2 → 0.7.12.0
3. Create detailed CHANGELOG.md entry
4. Update ARCHITECTURE_ANALYSIS.md provider sections
5. Include all modified files with absolute paths
6. Add testing recommendations

This guide ensures consistent, comprehensive documentation every time changes are made to WhisPad.
