import os
os.environ.setdefault("ADMIN_PASSWORD", "secret")
import pytest
from backend import app, HASHER
from db import pool, init_db, create_user, get_user

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with pool.connection() as conn:
        conn.execute('DELETE FROM users')
        conn.commit()
    create_user('admin', HASHER.hash('secret'), True, [], [])
    yield
    with pool.connection() as conn:
        conn.execute('DELETE FROM users')
        conn.commit()


def test_login_ok(setup_db):
    client = app.test_client()
    resp = client.post('/api/login', json={'username': 'admin', 'password': 'secret'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_login_ko(setup_db):
    client = app.test_client()
    resp = client.post('/api/login', json={'username': 'admin', 'password': 'wrong'})
    assert resp.status_code == 401
    assert resp.get_json()['success'] is False


def test_auto_rehash(setup_db):
    from argon2 import PasswordHasher
    from argon2.low_level import Type

    old_hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID)
    old_hash = old_hasher.hash('pass')
    create_user('user1', old_hash, False, [], [])

    client = app.test_client()
    resp = client.post('/api/login', json={'username': 'user1', 'password': 'pass'})
    assert resp.status_code == 200
    new_hash = get_user('user1')['password']
    assert new_hash != old_hash

