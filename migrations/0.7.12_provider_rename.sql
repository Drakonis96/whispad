-- WhisPad Provider Renaming Migration Script
-- Version: 0.7.12.0
-- Date: August 9, 2025
-- Purpose: Rename transcription providers for better consistency

-- PROVIDER RENAMING:
-- openai     → openai-api
-- local      → whisper-cpp  
-- sensevoice → funasr

BEGIN;

-- Create a backup table for safety
CREATE TABLE users_backup_0712 AS SELECT * FROM users;

-- Update transcription providers in users table
UPDATE users 
SET transcription_providers = array_replace(
        array_replace(
            array_replace(transcription_providers, 'openai', 'openai-api'),
            'local', 'whisper-cpp'
        ), 
        'sensevoice', 'funasr'
    );

-- Update postprocess providers in users table (only openai changes)
UPDATE users 
SET postprocess_providers = array_replace(postprocess_providers, 'openai', 'openai-api');

-- Update user preferences - transcription provider
UPDATE user_preferences 
SET preference_value = 'openai-api' 
WHERE preference_key = 'transcriptionProvider' AND preference_value = 'openai';

UPDATE user_preferences 
SET preference_value = 'whisper-cpp' 
WHERE preference_key = 'transcriptionProvider' AND preference_value = 'local';

UPDATE user_preferences 
SET preference_value = 'funasr' 
WHERE preference_key = 'transcriptionProvider' AND preference_value = 'sensevoice';

-- Update user preferences - postprocess provider (only openai)
UPDATE user_preferences 
SET preference_value = 'openai-api' 
WHERE preference_key = 'postprocessProvider' AND preference_value = 'openai';

-- Add migration record
INSERT INTO settings (key, value) VALUES 
('migration_0712_provider_rename', 'completed')
ON CONFLICT (key) DO UPDATE SET 
    value = 'completed',
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Verification queries (uncomment to check results)
-- SELECT username, transcription_providers, postprocess_providers FROM users;
-- SELECT username, preference_key, preference_value FROM user_preferences 
--   WHERE preference_key IN ('transcriptionProvider', 'postprocessProvider');
-- SELECT * FROM settings WHERE key = 'migration_0712_provider_rename';
