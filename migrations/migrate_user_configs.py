"""
WhisPad User Configuration Migration Script
Version: 0.7.12.0
Date: August 9, 2025
Purpose: Migrate user configurations stored in files and preferences
"""

import os
import json
import glob
import logging
from pathlib import Path
from provider_compatibility import migrate_user_config, migrate_provider_arrays

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def migrate_saved_notes_metadata():
    """
    Migrate metadata files in saved_notes directory.
    These may contain user preferences or provider references.
    """
    saved_notes_dir = Path("../saved_notes")
    if not saved_notes_dir.exists():
        logging.warning("saved_notes directory not found")
        return
    
    migrated_count = 0
    
    # Find all .meta files
    for meta_file in saved_notes_dir.rglob("*.meta"):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check if metadata contains provider references
            original_metadata = metadata.copy()
            
            # Migrate any provider references in metadata
            if 'transcriptionProvider' in metadata:
                metadata = migrate_user_config(metadata)
            
            # Save if changed
            if metadata != original_metadata:
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logging.info(f"Migrated metadata: {meta_file}")
                migrated_count += 1
                
        except Exception as e:
            logging.error(f"Error migrating {meta_file}: {e}")
    
    logging.info(f"Migrated {migrated_count} metadata files")


def migrate_user_config_files():
    """
    Migrate any user configuration files that might exist.
    Look for JSON files that might contain user settings.
    """
    # Common locations for config files
    config_patterns = [
        "../user_data/*.json",
        "../config/*.json", 
        "../*.config.json"
    ]
    
    migrated_count = 0
    
    for pattern in config_patterns:
        for config_file in glob.glob(pattern):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                original_config = config.copy()
                
                # Migrate configuration
                if isinstance(config, dict):
                    config = migrate_user_config(config)
                    
                    # Also handle provider arrays if they exist
                    if 'transcriptionProviders' in config:
                        config['transcriptionProviders'] = migrate_provider_arrays(
                            config['transcriptionProviders']
                        )
                    if 'postprocessProviders' in config:
                        config['postprocessProviders'] = migrate_provider_arrays(
                            config['postprocessProviders']
                        )
                
                # Save if changed
                if config != original_config:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2)
                    logging.info(f"Migrated config file: {config_file}")
                    migrated_count += 1
                    
            except Exception as e:
                logging.error(f"Error migrating config file {config_file}: {e}")
    
    logging.info(f"Migrated {migrated_count} configuration files")


def migrate_test_files():
    """
    Update test files that might contain hardcoded provider names.
    """
    test_patterns = [
        "../test*.py",
        "../tests/*.py"
    ]
    
    # Simple text replacements for test files
    replacements = {
        "'openai'": "'openai-api'",
        '"openai"': '"openai-api"',
        "'local'": "'whisper-cpp'", 
        '"local"': '"whisper-cpp"',
        "'sensevoice'": "'funasr'",
        '"sensevoice"': '"funasr"'
    }
    
    migrated_count = 0
    
    for pattern in test_patterns:
        for test_file in glob.glob(pattern):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply replacements
                for old, new in replacements.items():
                    content = content.replace(old, new)
                
                # Save if changed
                if content != original_content:
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logging.info(f"Migrated test file: {test_file}")
                    migrated_count += 1
                    
            except Exception as e:
                logging.error(f"Error migrating test file {test_file}: {e}")
    
    logging.info(f"Migrated {migrated_count} test files")


def create_migration_log():
    """
    Create a log file documenting the migration.
    """
    log_content = {
        "migration_version": "0.7.12.0",
        "migration_date": "2025-08-09",
        "migration_type": "provider_rename",
        "changes": {
            "openai": "openai-api",
            "local": "whisper-cpp", 
            "sensevoice": "funasr"
        },
        "status": "completed",
        "files_migrated": {
            "database": "via SQL script",
            "metadata_files": "automated",
            "config_files": "automated", 
            "test_files": "automated"
        }
    }
    
    with open("migration_0712_log.json", 'w') as f:
        json.dump(log_content, f, indent=2)
    
    logging.info("Created migration log: migration_0712_log.json")


def main():
    """
    Run the complete configuration migration process.
    """
    logging.info("Starting WhisPad 0.7.12 Provider Migration")
    logging.info("=" * 50)
    
    # Step 1: Migrate saved notes metadata
    logging.info("Step 1: Migrating saved notes metadata...")
    migrate_saved_notes_metadata()
    
    # Step 2: Migrate user config files
    logging.info("Step 2: Migrating user configuration files...")
    migrate_user_config_files()
    
    # Step 3: Migrate test files
    logging.info("Step 3: Migrating test files...")
    migrate_test_files()
    
    # Step 4: Create migration log
    logging.info("Step 4: Creating migration log...")
    create_migration_log()
    
    logging.info("=" * 50)
    logging.info("Migration completed successfully!")
    logging.info("Next steps:")
    logging.info("1. Run the database migration: 0.7.12_provider_rename.sql")
    logging.info("2. Update the main application code files")
    logging.info("3. Test the application thoroughly")
    logging.info("4. Deploy the changes")


if __name__ == "__main__":
    main()
