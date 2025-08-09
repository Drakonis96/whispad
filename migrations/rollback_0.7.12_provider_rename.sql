-- WhisPad Provider Renaming Rollback Script
-- Version: 0.7.12.0
-- Date: August 9, 2025
-- Purpose: Rollback provider renaming if needed

-- ROLLBACK MAPPING:
-- openai-api  → openai
-- whisper-cpp → local  
-- funasr      → sensevoice

BEGIN;

-- Verify backup table exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users_backup_0712') THEN
        RAISE EXCEPTION 'Backup table users_backup_0712 not found. Cannot safely rollback.';
    END IF;
END
$$;

-- Restore from backup (safest approach)
TRUNCATE users;
INSERT INTO users SELECT * FROM users_backup_0712;

-- Alternative: Manual rollback (uncomment if you prefer to keep any new users created after migration)
/*
-- Rollback transcription providers in users table
UPDATE users 
SET transcription_providers = array_replace(
        array_replace(
            array_replace(transcription_providers, 'openai-api', 'openai'),
            'whisper-cpp', 'local'
        ), 
        'funasr', 'sensevoice'
    );

-- Rollback postprocess providers in users table
UPDATE users 
SET postprocess_providers = array_replace(postprocess_providers, 'openai-api', 'openai');

-- Rollback user preferences - transcription provider
UPDATE user_preferences 
SET preference_value = 'openai' 
WHERE preference_key = 'transcriptionProvider' AND preference_value = 'openai-api';

UPDATE user_preferences 
SET preference_value = 'local' 
WHERE preference_key = 'transcriptionProvider' AND preference_value = 'whisper-cpp';

UPDATE user_preferences 
SET preference_value = 'sensevoice' 
WHERE preference_key = 'transcriptionProvider' AND preference_value = 'funasr';

-- Rollback user preferences - postprocess provider
UPDATE user_preferences 
SET preference_value = 'openai' 
WHERE preference_key = 'postprocessProvider' AND preference_value = 'openai-api';
*/

-- Update migration record
UPDATE settings 
SET value = 'rolled_back', updated_at = CURRENT_TIMESTAMP
WHERE key = 'migration_0712_provider_rename';

COMMIT;

-- Verification queries
SELECT 'Rollback completed successfully' as status;
SELECT username, transcription_providers, postprocess_providers FROM users LIMIT 5;
