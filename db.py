import os
import json
from psycopg_pool import ConnectionPool

DB_DSN = os.getenv("DATABASE_URL")
if not DB_DSN:
    raise RuntimeError("DATABASE_URL environment variable not set")

pool = ConnectionPool(conninfo=DB_DSN, min_size=1, max_size=5)


def init_db():
    """Create tables if they don't exist."""
    with pool.connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL,
                transcription_providers TEXT[] NOT NULL DEFAULT '{}',
                postprocess_providers TEXT[] NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                username TEXT NOT NULL,
                preference_key VARCHAR(255) NOT NULL,
                preference_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (username, preference_key),
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS study_items (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                type VARCHAR(20) NOT NULL CHECK (type IN ('quiz', 'flashcards')),
                title TEXT NOT NULL,
                content JSONB NOT NULL,
                source_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_study_items_username_type 
            ON study_items (username, type)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_study_items_created_at 
            ON study_items (created_at DESC)
            """
        )
        conn.commit()


def get_user(username: str):
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT username, password, is_admin, transcription_providers, postprocess_providers FROM users WHERE username=%s",
            [username],
        )
        row = cur.fetchone()
        if row:
            return {
                "username": row[0],
                "password": row[1],
                "is_admin": row[2],
                "transcription_providers": row[3] or [],
                "postprocess_providers": row[4] or [],
            }
        return None


def list_users():
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT username, is_admin, transcription_providers, postprocess_providers FROM users"
        )
        return [
            {
                "username": r[0],
                "is_admin": r[1],
                "transcription_providers": r[2] or [],
                "postprocess_providers": r[3] or [],
            }
            for r in cur.fetchall()
        ]


def create_user(username: str, password_hash: str, is_admin: bool, tp=None, pp=None):
    tp = tp or []
    pp = pp or []
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password, is_admin, transcription_providers, postprocess_providers) VALUES (%s, %s, %s, %s, %s)",
            [username, password_hash, is_admin, tp, pp],
        )
        conn.commit()


def update_password(username: str, password_hash: str):
    with pool.connection() as conn:
        conn.execute("UPDATE users SET password=%s WHERE username=%s", [password_hash, username])
        conn.commit()


def update_user_providers(username: str, tp=None, pp=None):
    tp = tp or []
    pp = pp or []
    with pool.connection() as conn:
        conn.execute(
            "UPDATE users SET transcription_providers=%s, postprocess_providers=%s WHERE username=%s",
            [tp, pp, username],
        )
        conn.commit()


def delete_user(username: str):
    with pool.connection() as conn:
        conn.execute("DELETE FROM users WHERE username=%s", [username])
        conn.commit()


def migrate_json(json_path="data/users.json", hasher=None):
    """Migrate users from a JSON file if table empty, or clean up leftover JSON file."""
    if not os.path.exists(json_path):
        return
    
    with pool.connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
    
    if count:
        # Database already has users, just remove the leftover JSON file
        print(f"Database already contains users. Removing leftover JSON file: {json_path}")
        os.remove(json_path)
        return
    
    # Perform migration if database is empty
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # If JSON is corrupted, just remove it
        print(f"Corrupted JSON file found. Removing: {json_path}")
        os.remove(json_path)
        return
    
    # Check if we need to update admin password from environment variable
    admin_password_env = os.getenv("ADMIN_PASSWORD")
    
    for username, info in data.items():
        password = info.get("password", "")
        
        # If this is the admin user and ADMIN_PASSWORD is set, use the env password
        if username == "admin" and admin_password_env:
            print(f"Using ADMIN_PASSWORD from environment for admin user during migration")
            password = admin_password_env
        
        if hasher:
            password = hasher.hash(password)
        create_user(
            username,
            password,
            info.get("is_admin", False),
            info.get("transcription_providers", []),
            info.get("postprocess_providers", []),
        )
    # Remove the JSON file after successful migration
    print(f"Migration completed successfully. Removing {json_path}")
    os.remove(json_path)


def get_setting(key: str, default_value: str = None):
    """Get a setting value from the database."""
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT value FROM settings WHERE key = %s",
            [key],
        )
        row = cur.fetchone()
        if row:
            return row[0]
        return default_value

def set_setting(key: str, value: str):
    """Set a setting value in the database."""
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """,
            [key, value],
        )
        conn.commit()

def get_all_settings():
    """Get all settings as a dictionary."""
    with pool.connection() as conn:
        cur = conn.execute("SELECT key, value FROM settings")
        return dict(cur.fetchall())

def migrate_server_config_to_db(json_path="data/server_config.json"):
    """Migrate server config from JSON file to database if it exists."""
    if not os.path.exists(json_path):
        return
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Migrate each setting to the database
        for key, value in data.items():
            set_setting(key, str(value))
        
        print(f"Server config migrated to database successfully. Removing {json_path}")
        os.remove(json_path)
    except Exception as e:
        print(f"Error migrating server config: {e}")


def get_user_preference(username: str, preference_key: str):
    """Get a user preference value."""
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT preference_value FROM user_preferences WHERE username=%s AND preference_key=%s",
            [username, preference_key],
        )
        row = cur.fetchone()
        return row[0] if row else None


# Study Items functions
def save_study_item(username: str, item_type: str, title: str, content: dict, source_content: str = None):
    """Save a quiz or flashcard set to the database."""
    with pool.connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO study_items (username, type, title, content, source_content)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            [username, item_type, title, json.dumps(content), source_content]
        )
        study_id = cur.fetchone()[0]
        conn.commit()
        return study_id


def save_individual_study_items(username: str, item_type: str, items: list, source_content: str = None, base_title: str = None):
    """Save individual questions or flashcards as separate study items."""
    saved_ids = []
    with pool.connection() as conn:
        for i, item in enumerate(items, 1):
            if item_type == 'quiz':
                # Save individual question
                title = f"Question {i}: {item.get('question', 'Untitled')[:50]}..."
                content = {"question": item}
            elif item_type == 'flashcards':
                # Save individual flashcard
                title = f"Flashcard {i}: {item.get('front', 'Untitled')[:50]}..."
                content = {"flashcard": item}
            else:
                continue
                
            # Add base title if provided
            if base_title:
                title = f"{base_title} - {title}"
            
            cur = conn.execute(
                """
                INSERT INTO study_items (username, type, title, content, source_content)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                [username, item_type, title, json.dumps(content), source_content]
            )
            study_id = cur.fetchone()[0]
            saved_ids.append(study_id)
        
        conn.commit()
    return saved_ids


def update_study_item_content(username: str, item_id: int, content: dict):
    """Update the content of an existing study item."""
    with pool.connection() as conn:
        cur = conn.execute(
            """
            UPDATE study_items 
            SET content = %s, updated_at = CURRENT_TIMESTAMP
            WHERE username = %s AND id = %s
            RETURNING id
            """,
            [json.dumps(content), username, item_id]
        )
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else None


def get_study_items(username: str, item_type: str = None):
    """Get all study items for a user, optionally filtered by type."""
    with pool.connection() as conn:
        if item_type:
            cur = conn.execute(
                """
                SELECT id, type, title, content, source_content, created_at, updated_at
                FROM study_items 
                WHERE username=%s AND type=%s 
                ORDER BY created_at DESC
                """,
                [username, item_type]
            )
        else:
            cur = conn.execute(
                """
                SELECT id, type, title, content, source_content, created_at, updated_at
                FROM study_items 
                WHERE username=%s 
                ORDER BY created_at DESC
                """,
                [username]
            )
        
        items = []
        for row in cur.fetchall():
            # PostgreSQL JSONB column returns dict directly, no need to parse
            content = row[3] if isinstance(row[3], dict) else json.loads(row[3]) if row[3] else {}
            items.append({
                'id': row[0],
                'type': row[1],
                'title': row[2],
                'content': content,
                'source_content': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None
            })
        
        return items


def get_study_item(username: str, item_id: int):
    """Get a specific study item by ID."""
    with pool.connection() as conn:
        cur = conn.execute(
            """
            SELECT id, type, title, content, source_content, created_at, updated_at
            FROM study_items 
            WHERE username=%s AND id=%s
            """,
            [username, item_id]
        )
        row = cur.fetchone()
        if row:
            # PostgreSQL JSONB column returns dict directly, no need to parse
            content = row[3] if isinstance(row[3], dict) else json.loads(row[3]) if row[3] else {}
            return {
                'id': row[0],
                'type': row[1],
                'title': row[2],
                'content': content,
                'source_content': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None
            }
        return None


def delete_study_item(username: str, item_id: int):
    """Delete a study item."""
    with pool.connection() as conn:
        cur = conn.execute(
            "DELETE FROM study_items WHERE username=%s AND id=%s",
            [username, item_id]
        )
        conn.commit()
        return cur.rowcount > 0


def delete_all_study_items_by_type(username: str, study_type: str):
    """Delete all study items of a specific type for a user."""
    with pool.connection() as conn:
        cur = conn.execute(
            "DELETE FROM study_items WHERE username=%s AND type=%s",
            [username, study_type]
        )
        conn.commit()
        return cur.rowcount


def set_user_preference(username: str, preference_key: str, preference_value: str):
    """Set a user preference value."""
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (username, preference_key, preference_value, updated_at) 
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (username, preference_key) 
            DO UPDATE SET preference_value = EXCLUDED.preference_value, updated_at = CURRENT_TIMESTAMP
            """,
            [username, preference_key, preference_value],
        )
        conn.commit()


def get_user_preferences(username: str):
    """Get all preferences for a user as a dictionary."""
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT preference_key, preference_value FROM user_preferences WHERE username=%s",
            [username],
        )
        return dict(cur.fetchall())


def get_all_questions_or_flashcards(username: str, item_type: str):
    """Get all questions or flashcards from all study items of a specific type for random selection."""
    with pool.connection() as conn:
        cur = conn.execute(
            """
            SELECT content
            FROM study_items 
            WHERE username=%s AND type=%s 
            ORDER BY created_at DESC
            """,
            [username, item_type]
        )
        
        all_items = []
        for row in cur.fetchall():
            # PostgreSQL JSONB column returns dict directly, no need to parse
            content = row[0] if isinstance(row[0], dict) else json.loads(row[0]) if row[0] else {}
            
            if item_type == 'quiz' and 'questions' in content:
                all_items.extend(content['questions'])
            elif item_type == 'flashcards' and 'flashcards' in content:
                all_items.extend(content['flashcards'])
        
        return all_items


