# WhisPad Migrations Directory

This directory contains all migration scripts and tools for WhisPad version upgrades that involve breaking changes.

## Current Migration: v0.7.12.0 - Provider Renaming

**Purpose**: Rename transcription providers for better consistency  
**Date**: August 9, 2025  
**Type**: Breaking Change  

### Provider Changes:
- `openai` → `openai-api`
- `local` → `whisper-cpp`  
- `sensevoice` → `funasr`

## Files in this Directory

### Migration Scripts
- **`0.7.12_provider_rename.sql`** - Database migration script
- **`rollback_0.7.12_provider_rename.sql`** - Database rollback script  
- **`execute_migration.py`** - Complete automated migration executor

### Support Files
- **`provider_compatibility.py`** - Backward compatibility layer and helper functions
- **`migrate_user_configs.py`** - Migrate user configuration files and metadata
- **`migration_guide.md`** - Comprehensive migration instructions

### Generated Files (Created during migration)
- **`migration_execution.log`** - Migration execution log
- **`migration_execution_log.json`** - Detailed migration results in JSON format
- **`migration_0712_log.json`** - User config migration log

## Quick Start

### Automated Migration (Recommended)
```bash
cd migrations
python execute_migration.py
```

### Manual Migration
```bash
# 1. Backup database
pg_dump whispad > whispad_backup_pre_0712.sql

# 2. Run database migration
psql -d whispad -f 0.7.12_provider_rename.sql

# 3. Migrate config files
python migrate_user_configs.py

# 4. Update application code (see migration_guide.md)
```

### Emergency Rollback
```bash
# Option 1: Restore from backup
psql -d whispad -f whispad_backup_pre_0712.sql

# Option 2: Use rollback script  
psql -d whispad -f rollback_0.7.12_provider_rename.sql
```

## Migration Safety

### What's Protected:
- ✅ Automatic database backup creation
- ✅ Transaction-based database migration (atomic)
- ✅ Rollback procedures available
- ✅ Validation checks at each step
- ✅ Detailed logging of all changes

### What Requires Manual Update:
- ⚠️ Application code files (`backend.py`, `app.js`, `index.html`, etc.)
- ⚠️ API endpoint testing
- ⚠️ UI functionality verification
- ⚠️ Provider-specific feature testing

## Testing Checklist

After migration, verify:
- [ ] Database shows new provider names
- [ ] Application starts without errors  
- [ ] All transcription providers work
- [ ] User permissions preserved
- [ ] Configuration UI updated
- [ ] No old provider references remain

## Support

1. **Check migration logs** in this directory
2. **Review `migration_guide.md`** for detailed instructions
3. **Use rollback procedures** if critical issues occur
4. **Test thoroughly** before production deployment

## Future Migrations

When adding new migrations:
1. Create new dated SQL file (e.g., `0.8.0_new_feature.sql`)
2. Add rollback script (`rollback_0.8.0_new_feature.sql`)
3. Update compatibility layer if needed
4. Create migration guide
5. Test thoroughly in development environment
