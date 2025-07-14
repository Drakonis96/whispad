import json
import os
import db

USERS_JSON = '/app/data/users.json'

def main():
    if not os.path.exists(USERS_JSON):
        print('No users.json found, nothing to migrate')
        return
    conn = db.get_connection()
    db.init_db(conn)
    with open(USERS_JSON, 'r', encoding='utf-8') as f:
        users = json.load(f)
    for login, info in users.items():
        pwd_hash = info.get('pwd_hash')
        password = info.get('password')
        if pwd_hash and not pwd_hash.startswith('$argon2id$'):
            pwd_hash = db.hash_password(password or pwd_hash)
        elif password:
            pwd_hash = db.hash_password(password)
        else:
            continue
        try:
            db.create_user(
                conn,
                login,
                password=password,
                is_admin=info.get('is_admin', False),
                tp=info.get('transcription_providers', []),
                pp=info.get('postprocess_providers', []),
                pwd_hash=pwd_hash,
            )
        except Exception:
            pass
    conn.commit()
    os.system(f'shred -u {USERS_JSON}')
    print('Migration completed')

if __name__ == '__main__':
    main()
