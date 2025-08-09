import time
from datetime import timedelta

import pytest

from src.core.utilities import TimedCache


@pytest.fixture
def idempotent_fetch_func():
    def f():
        return 42

    return f


class TestTimedCache:
    def test_create_cache(self):
        cache = TimedCache[str, int]()
        assert isinstance(cache, TimedCache)

    def test_get_or_fetch_no_values_in_cache(self):
        cache = TimedCache[str, int]()

        assert not cache.get_all_from_key("test")

    def test_get_or_fetch_single(self):
        cache = TimedCache[str, int]()

        def fetch_func():
            return 42

        value, fetched_time = cache.get_or_fetch("test", fetch_func, timedelta(minutes=5))
        assert value == 42

        # Should return cached value
        cached, fetched_time = cache.get_or_fetch("test", fetch_func, timedelta(minutes=5))
        assert cached == 42

    def test_get_all_single(self):
        cache = TimedCache[str, int]()

        def fetch_func():
            return 42

        cache.get_or_fetch("test", fetch_func, timedelta(minutes=5))
        data = cache.get_all_from_key("test")

        assert data, "should have one value in cache"
        values = [i[0] for i in data]

        assert len(values) == 1
        assert values[0] == 42

    def test_get_or_fetch_multiple(self):
        cache = TimedCache[str, int]()
        counter = 0

        def fetch_func():
            nonlocal counter
            counter += 1
            return counter

        # First fetch
        value1, fetched_time = cache.get_or_fetch("test", fetch_func, timedelta(minutes=5))
        assert value1 == 1

        # Force expiration
        time.sleep(0.1)
        value2, fetched_time = cache.get_or_fetch("test", fetch_func, timedelta(microseconds=1))
        assert value2 == 2

    def test_get_or_fetch_with_duplicate_entries(self, idempotent_fetch_func):
        cache = TimedCache[str, int]()
        key = "test"

        # First fetch
        r, fetched_time = cache.get_or_fetch(key, idempotent_fetch_func, timedelta(microseconds=1))
        r1 = cache.get_all_from_key(key)
        assert r
        assert r1
        assert r == r1[0][0]
        assert len(r1) == 1

        cache.get_or_fetch(key, idempotent_fetch_func, timedelta(microseconds=1))
        r2 = cache.get_all_from_key(key)

        assert r2
        assert len(r2) == 1

    def test_get_all_multiple(self):
        cache = TimedCache[str, int]()
        counter = 0

        def fetch_func():
            nonlocal counter
            counter += 1
            return counter

        # Multiple fetches
        cache.get_or_fetch("test", fetch_func, timedelta(minutes=5))
        time.sleep(0.1)
        cache.get_or_fetch("test", fetch_func, timedelta(microseconds=1))

        data = cache.get_all_from_key("test")
        assert data, "should have one value in cache"
        values = [i[0] for i in data]

        assert len(values) == 2
        assert values[0] == 1
        assert values[1] == 2

    def test_invalidate(self):
        cache = TimedCache[str, int]()

        def fetch_func():
            return 42

        cache.get_or_fetch("test", fetch_func, timedelta(minutes=5))
        cache.invalidate("test")

        assert cache.get_all_from_key("test") is None

    def test_clear(self):
        cache = TimedCache[str, int]()

        def fetch_func():
            return 42

        cache.get_or_fetch("test1", fetch_func, timedelta(minutes=5))
        cache.get_or_fetch("test2", fetch_func, timedelta(minutes=5))

        cache.clear()
        assert cache.get_all_from_key("test1") is None
        assert cache.get_all_from_key("test2") is None
