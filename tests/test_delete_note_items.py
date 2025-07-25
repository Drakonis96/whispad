import os
import json
import pytest
from backend import app, HASHER
from db import pool, init_db, create_user, save_individual_study_items

os.environ.setdefault("ADMIN_PASSWORD", "secret")

@pytest.fixture(autouse=True)
def setup_env(tmp_path):
    init_db()
    with pool.connection() as conn:
        conn.execute('DELETE FROM users')
        conn.execute('DELETE FROM study_items')
        conn.commit()
    create_user('admin', HASHER.hash('secret'), True, [], [])

    # Prepare note files
    notes_dir = tmp_path / 'saved_notes' / 'admin'
    notes_dir.mkdir(parents=True)
    note_id = 'testnote'
    (notes_dir / 'note.md').write_text('# Title\nContent')
    (notes_dir / 'note.md.meta').write_text(json.dumps({'id': note_id, 'title': 'note'}))

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield {'note_id': note_id}
    os.chdir(old_cwd)
    with pool.connection() as conn:
        conn.execute('DELETE FROM users')
        conn.execute('DELETE FROM study_items')
        conn.commit()


def test_delete_note_removes_study_items(setup_env):
    note_id = setup_env['note_id']
    # create a study item linked to note
    save_individual_study_items('admin', 'quiz', [{'question': 'Q1', 'answers': ['A'], 'correct_answer': 0}], source_content='Content', base_title='Quiz', note_id=note_id)

    client = app.test_client()
    resp = client.post('/api/login', json={'username': 'admin', 'password': 'secret'})
    token = resp.get_json()['token']

    resp = client.post('/api/delete-note', json={'id': note_id}, headers={'Authorization': token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data.get('deleted_study_items', 0) >= 1
    # verify no study items remain
    with pool.connection() as conn:
        cur = conn.execute('SELECT COUNT(*) FROM study_items WHERE note_id=%s', [note_id])
        count = cur.fetchone()[0]
    assert count == 0

