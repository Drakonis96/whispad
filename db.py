import os
import json
from psycopg_pool import ConnectionPool

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/whispad")

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
    """Migrate users from a JSON file if table empty."""
    if not os.path.exists(json_path):
        return
    with pool.connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
    if count:
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    for username, info in data.items():
        password = info.get("password", "")
        if hasher:
            password = hasher.hash(password)
        create_user(
            username,
            password,
            info.get("is_admin", False),
            info.get("transcription_providers", []),
            info.get("postprocess_providers", []),
        )
    backup = json_path + ".bak"
    os.rename(json_path, backup)


