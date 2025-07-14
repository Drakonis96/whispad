import os
import json
import psycopg2
import sqlite3
from contextlib import closing
from argon2 import PasswordHasher, exceptions

PH = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)


def get_connection():
    if os.environ.get('WHISPAD_TEST_DB') == 'sqlite':
        path = os.environ.get('WHISPAD_TEST_DB_FILE', ':memory:')
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    params = {
        'host': os.environ['PGHOST'],
        'port': int(os.environ.get('PGPORT', 5432)),
        'dbname': os.environ['PGDATABASE'],
        'user': os.environ['PGUSER'],
        'password': os.environ['PGPASSWORD'],
        'sslmode': os.environ.get('PGSSLMODE', 'require'),
    }
    return psycopg2.connect(**params)


def init_db(conn):
    cur = conn.cursor()
    if isinstance(conn, sqlite3.Connection):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE,
                pwd_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                transcription_providers TEXT,
                postprocess_providers TEXT,
                creado_en TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id BIGSERIAL PRIMARY KEY,
                login TEXT UNIQUE,
                pwd_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                transcription_providers TEXT[],
                postprocess_providers TEXT[],
                creado_en TIMESTAMPTZ DEFAULT now()
            )
            """
        )
    conn.commit()


def hash_password(password: str) -> str:
    return PH.hash(password)


def verify_password(stored: str, password: str) -> bool:
    try:
        return PH.verify(stored, password)
    except exceptions.VerifyMismatchError:
        return False


def check_needs_rehash(stored: str) -> bool:
    return PH.check_needs_rehash(stored)


def get_user(conn, login: str):
    cur = conn.cursor()
    if isinstance(conn, sqlite3.Connection):
        cur.execute("SELECT * FROM usuarios WHERE login = ?", (login,))
    else:
        cur.execute("SELECT * FROM usuarios WHERE login = %s", (login,))
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(conn, sqlite3.Connection):
        row = dict(zip([c[0] for c in cur.description], row))
        if row.get('transcription_providers'):
            row['transcription_providers'] = json.loads(row['transcription_providers'])
        if row.get('postprocess_providers'):
            row['postprocess_providers'] = json.loads(row['postprocess_providers'])
    return row


def create_user(conn, login: str, password: str = None, is_admin=False, tp=None, pp=None, pwd_hash=None):
    tp = tp or []
    pp = pp or []
    if pwd_hash is None:
        pwd_hash = hash_password(password or '')
    cur = conn.cursor()
    if isinstance(conn, sqlite3.Connection):
        cur.execute(
            "INSERT INTO usuarios (login, pwd_hash, is_admin, transcription_providers, postprocess_providers) VALUES (?, ?, ?, ?, ?)",
            (login, pwd_hash, int(is_admin), json.dumps(tp), json.dumps(pp)),
        )
    else:
        cur.execute(
            "INSERT INTO usuarios (login, pwd_hash, is_admin, transcription_providers, postprocess_providers) VALUES (%s, %s, %s, %s, %s)",
            (login, pwd_hash, is_admin, tp, pp),
        )
    conn.commit()
    return pwd_hash


def update_password_hash(conn, login: str, pwd_hash: str):
    cur = conn.cursor()
    if isinstance(conn, sqlite3.Connection):
        cur.execute("UPDATE usuarios SET pwd_hash = ? WHERE login = ?", (pwd_hash, login))
    else:
        cur.execute("UPDATE usuarios SET pwd_hash = %s WHERE login = %s", (pwd_hash, login))
    conn.commit()


def update_user_info(conn, login: str, is_admin=None, tp=None, pp=None):
    cur = conn.cursor()
    fields = []
    params = []
    if is_admin is not None:
        fields.append('is_admin = %s' if not isinstance(conn, sqlite3.Connection) else 'is_admin = ?')
        params.append(is_admin)
    if tp is not None:
        if isinstance(conn, sqlite3.Connection):
            fields.append('transcription_providers = ?')
            params.append(json.dumps(tp))
        else:
            fields.append('transcription_providers = %s')
            params.append(tp)
    if pp is not None:
        if isinstance(conn, sqlite3.Connection):
            fields.append('postprocess_providers = ?')
            params.append(json.dumps(pp))
        else:
            fields.append('postprocess_providers = %s')
            params.append(pp)
    if not fields:
        return
    if isinstance(conn, sqlite3.Connection):
        params.append(login)
        cur.execute(f"UPDATE usuarios SET {', '.join(fields)} WHERE login = ?", params)
    else:
        params.append(login)
        cur.execute(f"UPDATE usuarios SET {', '.join(fields)} WHERE login = %s", params)
    conn.commit()


def list_users(conn):
    cur = conn.cursor()
    cur.execute("SELECT login, is_admin, transcription_providers, postprocess_providers FROM usuarios")
    rows = cur.fetchall()
    result = []
    for r in rows:
        if isinstance(conn, sqlite3.Connection):
            r = dict(zip([c[0] for c in cur.description], r))
            if r.get('transcription_providers'):
                r['transcription_providers'] = json.loads(r['transcription_providers'])
            if r.get('postprocess_providers'):
                r['postprocess_providers'] = json.loads(r['postprocess_providers'])
        result.append(r)
    return result


def delete_user(conn, login: str):
    cur = conn.cursor()
    if isinstance(conn, sqlite3.Connection):
        cur.execute("DELETE FROM usuarios WHERE login = ?", (login,))
    else:
        cur.execute("DELETE FROM usuarios WHERE login = %s", (login,))
    conn.commit()

