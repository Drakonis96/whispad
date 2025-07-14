import time
import db


def test_argon2_speed():
    start = time.perf_counter()
    db.hash_password('benchmark')
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 400, f"hash took {elapsed}ms"

