# WhisPad 0.7.12 Provider Migration Guide

**Migration Date**: August 9, 2025  
**Version**: 0.7.12.0  
**Type**: Breaking Changes - Provider Renaming  
**Impact**: Critical - Requires Migration

## Overview

This migration renames transcription providers for better consistency:

- `openai` → `openai-api`
- `local` → `whisper-cpp`  
- `sensevoice` → `funasr`

## ⚠️ IMPORTANT WARNINGS

- **This is a BREAKING CHANGE** - existing configurations will not work without migration
- **Backup your database** before running the migration
- **Test thoroughly** in a development environment first
- **Users will need to update** their saved configurations

## 📋 Migration Steps (REQUIRED ORDER)

### Step 1: Backup Database
```bash
# PostgreSQL backup
pg_dump whispad > whispad_backup_pre_0712.sql

# Alternative: Create backup via psql
psql -d whispad -c "CREATE TABLE users_backup_0712 AS SELECT * FROM users;"
```

### Step 2: Run Database Migration
```bash
# Connect to your database
psql -d whispad -f migrations/0.7.12_provider_rename.sql
```

### Step 3: Migrate User Configuration Files
```bash
cd migrations
python migrate_user_configs.py
```

### Step 4: Update Application Code
Update the following files in this order:

#### A. Backend Core Files (CRITICAL)
1. **`backend.py`** - Update provider constants and routing logic
2. **`db.py`** - No changes needed (handled by SQL migration)

#### B. Frontend Files (CRITICAL)  
3. **`app.js`** - Update provider constants and validation
4. **`backend-api.js`** - Update API parameter handling
5. **`index.html`** - Update UI option values

#### C. Supporting Files
6. **AI processing files** - Update provider references
7. **Test files** - Update hardcoded values
8. **Documentation** - Update provider references

### Step 5: Test the Migration
```bash
# Test database migration
psql -d whispad -c "SELECT username, transcription_providers FROM users LIMIT 5;"

# Test application startup
python backend.py

# Test frontend (open in browser)
# Check provider dropdowns show new names
# Test transcription with each provider
```

## 🔄 Rollback Procedure (If Needed)

### Emergency Rollback
```bash
# Option 1: Restore from backup
psql -d whispad -f whispad_backup_pre_0712.sql

# Option 2: Use rollback script
psql -d whispad -f migrations/rollback_0.7.12_provider_rename.sql
```

### Code Rollback
1. Revert code changes to previous commit
2. Restart application
3. Verify functionality

## 📁 File Changes Required

### Critical Files (Will Break Without Updates)
- `backend.py` - Line 148, provider routing
- `app.js` - Lines 189, 1108, 6820, 7673+, 8119+
- `index.html` - Lines 34-36, 586-588
- `backend-api.js` - Provider parameter handling

### Supporting Files
- `ai_reprocess*.py` - Provider references  
- `ai_suggestions.py` - Provider checks
- `test_*.py` - Hardcoded provider names
- Documentation files

## 🧪 Testing Checklist

### Database Tests
- [ ] Users table shows new provider names
- [ ] User preferences updated correctly
- [ ] No duplicate or null providers
- [ ] Migration status recorded in settings

### Application Tests  
- [ ] Application starts without errors
- [ ] Provider dropdowns show new names
- [ ] OpenAI API transcription works
- [ ] Local whisper.cpp transcription works  
- [ ] FunASR (SenseVoice) transcription works
- [ ] User permissions preserved
- [ ] AI enhancement still works

### UI Tests
- [ ] Config modal shows correct providers
- [ ] Models modal works with new provider names
- [ ] User creation/editing works
- [ ] Provider selection persists correctly

## 🔍 Verification Queries

```sql
-- Check migration status
SELECT * FROM settings WHERE key = 'migration_0712_provider_rename';

-- Verify user providers
SELECT username, transcription_providers, postprocess_providers 
FROM users;

-- Check user preferences
SELECT username, preference_key, preference_value 
FROM user_preferences 
WHERE preference_key IN ('transcriptionProvider', 'postprocessProvider');

-- Verify no old provider names remain
SELECT COUNT(*) as old_transcription_refs
FROM users 
WHERE 'openai' = ANY(transcription_providers) 
   OR 'local' = ANY(transcription_providers)
   OR 'sensevoice' = ANY(transcription_providers);
-- Should return 0

SELECT COUNT(*) as old_preference_refs
FROM user_preferences 
WHERE preference_value IN ('openai', 'local', 'sensevoice')
  AND preference_key LIKE '%Provider';
-- Should return 0
```

## 📊 Expected Results

### Before Migration
```json
{
  "transcription_providers": ["openai", "local", "sensevoice"],
  "user_config": {
    "transcriptionProvider": "openai",
    "postprocessProvider": "openai"
  }
}
```

### After Migration  
```json
{
  "transcription_providers": ["openai-api", "whisper-cpp", "funasr"],
  "user_config": {
    "transcriptionProvider": "openai-api", 
    "postprocessProvider": "openai-api"
  }
}
```

## 🚨 Troubleshooting

### Common Issues

**"Unknown provider" errors**
- Check that all code files are updated with new provider names
- Verify database migration completed successfully

**Frontend shows old provider names**
- Clear browser cache
- Check `index.html` option values updated
- Verify `app.js` provider constants updated

**Database migration fails** 
- Check PostgreSQL user permissions
- Verify backup table doesn't already exist
- Review migration log for specific errors

**Users can't transcribe**
- Check provider permissions in database
- Verify API keys still configured correctly
- Test each provider individually

### Support Commands

```bash
# Check application logs
tail -f logs/whispad.log

# Test database connection
psql -d whispad -c "SELECT version();"

# Verify migration files
ls -la migrations/

# Check Python imports
python -c "from migrations.provider_compatibility import migrate_provider_name; print('OK')"
```

## 📞 Support

If you encounter issues during migration:

1. **Check the migration log**: `migrations/migration_0712_log.json`
2. **Review application logs** for specific error messages  
3. **Use rollback procedures** if critical errors occur
4. **Test in development environment** before production deployment

## ✅ Post-Migration Checklist

- [ ] Database migration completed successfully
- [ ] Application starts without errors
- [ ] All provider types work correctly
- [ ] User permissions preserved
- [ ] Configuration UI updated
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Migration logged and verified

**Remember**: This is a major version change (0.7.11 → 0.7.12) due to breaking changes. Communicate the migration requirements to all users and administrators.
