import os
os.environ.setdefault("ADMIN_PASSWORD", "benchmark")
from backend import HASHER


def test_hash_performance(benchmark):
    benchmark(lambda: HASHER.hash('benchmark'))
    assert benchmark.stats.stats.mean < 0.4

