"""
WhisPad Migration Executor
Version: 0.7.12.0
Date: August 9, 2025
Purpose: Execute the complete provider renaming migration safely
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from provider_compatibility import (
    migrate_provider_name,
    migrate_user_config, 
    migrate_provider_arrays,
    PROVIDER_MIGRATION_MAP
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_execution.log'),
        logging.StreamHandler()
    ]
)

class MigrationExecutor:
    def __init__(self):
        self.migration_log = {
            "start_time": datetime.now().isoformat(),
            "version": "0.7.12.0",
            "type": "provider_rename",
            "steps_completed": [],
            "errors": [],
            "status": "in_progress"
        }
    
    def log_step(self, step_name, success=True, details=None):
        """Log a migration step"""
        step_info = {
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "details": details or {}
        }
        
        if success:
            self.migration_log["steps_completed"].append(step_info)
            logging.info(f"✅ {step_name}")
        else:
            self.migration_log["errors"].append(step_info)
            logging.error(f"❌ {step_name}: {details}")
    
    def check_prerequisites(self):
        """Check that all prerequisites are met"""
        logging.info("Checking prerequisites...")
        
        # Check if running from correct directory
        if not Path("../backend.py").exists():
            self.log_step("Check prerequisites", False, 
                         {"error": "Not running from migrations directory or backend.py not found"})
            return False
        
        # Check if database is accessible (if DATABASE_URL is set)
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            try:
                # Try to connect to database
                import psycopg
                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                logging.info("Database connection successful")
            except Exception as e:
                self.log_step("Database connection", False, {"error": str(e)})
                return False
        
        # Check if backup can be created
        backup_dir = Path("../backups")
        backup_dir.mkdir(exist_ok=True)
        
        self.log_step("Prerequisites check", True)
        return True
    
    def create_backups(self):
        """Create backups before migration"""
        logging.info("Creating backups...")
        
        try:
            # Create timestamp for backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path("../backups")
            backup_dir.mkdir(exist_ok=True)
            
            # List of critical files to backup
            critical_files = [
                "../backend.py",
                "../app.js", 
                "../index.html",
                "../backend-api.js",
                "../db.py"
            ]
            
            backup_info = {"timestamp": timestamp, "files_backed_up": []}
            
            for file_path in critical_files:
                if Path(file_path).exists():
                    backup_name = f"{Path(file_path).stem}_{timestamp}.backup"
                    backup_path = backup_dir / backup_name
                    
                    # Copy file
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    backup_info["files_backed_up"].append(str(backup_path))
                    
            self.log_step("Create file backups", True, backup_info)
            return True
            
        except Exception as e:
            self.log_step("Create backups", False, {"error": str(e)})
            return False
    
    def execute_database_migration(self):
        """Execute the database migration"""
        logging.info("Executing database migration...")
        
        try:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self.log_step("Database migration", False, 
                             {"error": "DATABASE_URL not set"})
                return False
            
            # Execute the migration SQL
            sql_file = Path("0.7.12_provider_rename.sql")
            if not sql_file.exists():
                self.log_step("Database migration", False,
                             {"error": "Migration SQL file not found"})
                return False
            
            import psycopg
            with psycopg.connect(db_url) as conn:
                with open(sql_file, 'r') as f:
                    sql_content = f.read()
                
                with conn.cursor() as cur:
                    cur.execute(sql_content)
                
                conn.commit()
            
            self.log_step("Database migration", True, 
                         {"sql_file": str(sql_file)})
            return True
            
        except Exception as e:
            self.log_step("Database migration", False, {"error": str(e)})
            return False
    
    def migrate_config_files(self):
        """Migrate configuration files"""
        logging.info("Migrating configuration files...")
        
        try:
            # Run the user config migration script
            from migrate_user_configs import main as migrate_configs_main
            migrate_configs_main()
            
            self.log_step("Config file migration", True)
            return True
            
        except Exception as e:
            self.log_step("Config file migration", False, {"error": str(e)})
            return False
    
    def validate_migration(self):
        """Validate that migration completed successfully"""
        logging.info("Validating migration...")
        
        try:
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                import psycopg
                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        # Check migration status
                        cur.execute(
                            "SELECT value FROM settings WHERE key = 'migration_0712_provider_rename'"
                        )
                        result = cur.fetchone()
                        
                        if not result or result[0] != 'completed':
                            self.log_step("Migration validation", False,
                                         {"error": "Migration not marked as completed in database"})
                            return False
                        
                        # Check for remaining old provider names
                        cur.execute("""
                            SELECT COUNT(*) FROM users 
                            WHERE 'openai' = ANY(transcription_providers) 
                               OR 'local' = ANY(transcription_providers)
                               OR 'sensevoice' = ANY(transcription_providers)
                        """)
                        old_provider_count = cur.fetchone()[0]
                        
                        if old_provider_count > 0:
                            self.log_step("Migration validation", False,
                                         {"error": f"Found {old_provider_count} users with old provider names"})
                            return False
            
            self.log_step("Migration validation", True)
            return True
            
        except Exception as e:
            self.log_step("Migration validation", False, {"error": str(e)})
            return False
    
    def finalize_migration(self):
        """Finalize the migration and create completion log"""
        self.migration_log["end_time"] = datetime.now().isoformat()
        self.migration_log["status"] = "completed" if not self.migration_log["errors"] else "completed_with_errors"
        
        # Save migration log
        with open("migration_execution_log.json", 'w') as f:
            json.dump(self.migration_log, f, indent=2)
        
        # Print summary
        logging.info("\n" + "="*60)
        logging.info("MIGRATION SUMMARY")
        logging.info("="*60)
        logging.info(f"Status: {self.migration_log['status']}")
        logging.info(f"Steps completed: {len(self.migration_log['steps_completed'])}")
        logging.info(f"Errors: {len(self.migration_log['errors'])}")
        
        if self.migration_log["errors"]:
            logging.warning("Errors encountered:")
            for error in self.migration_log["errors"]:
                logging.warning(f"  - {error['step']}: {error['details']}")
        
        logging.info("="*60)
    
    def execute_full_migration(self):
        """Execute the complete migration process"""
        logging.info("Starting WhisPad 0.7.12 Provider Migration")
        logging.info("="*60)
        
        # Step 1: Prerequisites
        if not self.check_prerequisites():
            logging.error("Prerequisites not met. Aborting migration.")
            return False
        
        # Step 2: Backups
        if not self.create_backups():
            logging.error("Backup creation failed. Aborting migration.")
            return False
        
        # Step 3: Database migration
        if not self.execute_database_migration():
            logging.error("Database migration failed. Check logs and consider rollback.")
            return False
        
        # Step 4: Config file migration  
        if not self.migrate_config_files():
            logging.warning("Config file migration had issues. Manual review may be needed.")
        
        # Step 5: Validation
        if not self.validate_migration():
            logging.error("Migration validation failed. Review and fix issues.")
            return False
        
        # Step 6: Finalization
        self.finalize_migration()
        
        logging.info("Migration completed successfully!")
        logging.info("Next steps:")
        logging.info("1. Update application code files (backend.py, app.js, etc.)")
        logging.info("2. Test the application thoroughly")
        logging.info("3. Deploy the changes")
        
        return True


def main():
    """Main execution function"""
    executor = MigrationExecutor()
    success = executor.execute_full_migration()
    
    if not success:
        logging.error("Migration failed. Check logs and consider rollback.")
        sys.exit(1)
    
    logging.info("Migration execution completed successfully.")


if __name__ == "__main__":
    main()
