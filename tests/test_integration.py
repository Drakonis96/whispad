from backend import app, HASHER
from db import pool, init_db, create_user


def test_integration_login():
    init_db()
    with pool.connection() as conn:
        conn.execute('DELETE FROM users')
        conn.commit()
    create_user('int', HASHER.hash('intpass'), False, [], [])
    client = app.test_client()
    resp = client.post('/api/login', json={'username': 'int', 'password': 'intpass'})
    assert resp.status_code == 200
    assert resp.get_json()['success']

