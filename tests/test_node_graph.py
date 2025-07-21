import os
os.environ.setdefault("ADMIN_PASSWORD", "nodepass")
from backend import app, HASHER
from db import pool, init_db, create_user


def setup_module(module):
    init_db()
    with pool.connection() as conn:
        conn.execute('DELETE FROM users')
        conn.commit()
    create_user('nodeuser', HASHER.hash('nodepass'), False, [], [])


def test_node_graph_endpoint():
    client = app.test_client()
    resp = client.post('/api/login', json={'username': 'nodeuser', 'password': 'nodepass'})
    assert resp.status_code == 200
    token = resp.get_json()['token']
    headers = {'Authorization': token}
    resp = client.post('/api/node-graph', json={'note': 'apple banana apple. banana cherry.'}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'nodes' in data and 'links' in data and 'insights' in data
