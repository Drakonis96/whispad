import os
import db

os.environ['WHISPAD_TEST_DB'] = 'sqlite'


def setup_db():
    conn = db.get_connection()
    db.init_db(conn)
    return conn


def test_login_ok():
    conn = setup_db()
    db.create_user(conn, 'user1', password='secret')
    user = db.get_user(conn, 'user1')
    assert db.verify_password(user['pwd_hash'], 'secret')


def test_login_fail():
    conn = setup_db()
    db.create_user(conn, 'user2', password='x')
    user = db.get_user(conn, 'user2')
    assert not db.verify_password(user['pwd_hash'], 'bad')


def test_rehash():
    conn = setup_db()
    # create hash with lower time_cost
    from argon2 import PasswordHasher
    old_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)
    old_hash = old_ph.hash('pw')
    db.create_user(conn, 'user3', pwd_hash=old_hash)
    user = db.get_user(conn, 'user3')
    assert db.verify_password(user['pwd_hash'], 'pw')
    assert db.check_needs_rehash(user['pwd_hash'])
    new_hash = db.hash_password('pw')
    db.update_password_hash(conn, 'user3', new_hash)
    user = db.get_user(conn, 'user3')
    assert not db.check_needs_rehash(user['pwd_hash'])


