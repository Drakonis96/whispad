import os
import json
import db
import tempfile

os.environ['WHISPAD_TEST_DB'] = 'sqlite'




def test_migration_script(tmp_path):
    # create sample users.json
    data = {
        "admin": {
            "password": "whispad",
            "is_admin": True
        }
    }
    users_file = tmp_path / 'users.json'
    with open(users_file, 'w') as f:
        json.dump(data, f)
    # Override path for script
    import migrate_users
    migrate_users.USERS_JSON = str(users_file)
    db_file = tmp_path / 'test.db'
    os.environ['WHISPAD_TEST_DB_FILE'] = str(db_file)
    conn = db.get_connection()
    db.init_db(conn)
    migrate_users.main()
    user = db.get_user(conn, 'admin')
    assert user is not None
    assert user['pwd_hash'].startswith('$argon2id$')
    assert not os.path.exists(users_file)

