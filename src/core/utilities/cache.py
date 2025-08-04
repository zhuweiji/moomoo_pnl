from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Callable, Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TimedCache(Generic[K, V]):
    """A generic time-based cache that stores key-value pairs with expiration.

    The cache maintains timestamps for each entry and provides mechanisms to fetch
    fresh data when cached values become stale based on a configurable time interval.

    Type Parameters:
        K: The type of the cache keys
        V: The type of the cached values

    Example:
        ```python
        # Create a cache with string keys and int values
        cache = TimedCache[str, int]()

        def fetch_value() -> int:
            return 42

        # Get or fetch with 5 minute expiration
        value = cache.get_or_fetch("key", fetch_value, timedelta(minutes=5))
        ```

    Note:
        The cache is not thread-safe by default. For thread-safe operations,
        use ThreadSafeTimedCache instead.
    """

    def __init__(self):
        self._cache: dict[K, list[tuple[V, datetime]]] = defaultdict(list)

    def get_or_fetch(self, key: K, fetch_func: Callable[[], V], max_age: timedelta) -> V:
        """
        Get item from cache if fresh, otherwise fetch new value.

        Args:
            key: Cache key
            fetch_func: Function to fetch new value if needed
            max_age: Maximum age before item is considered stale

        Returns:
            Latest cached or newly fetched value
        """
        now = datetime.now()

        if key in self._cache:
            previous_values = self._cache[key]
            latest_value, latest_timestamp = previous_values[-1]
            if now - latest_timestamp <= max_age:
                return latest_value

        # Fetch new value if not in cache or stale
        new_value = fetch_func()
        self._cache[key].append((new_value, now))
        return new_value

    def get_all(self, key: K):
        """Retrieves all previously fetched vales for a given key"""
        return self._cache.get(key, None)

    def invalidate(self, key: K) -> None:
        """Remove an item from the cache"""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all items from the cache"""
        self._cache.clear()


class ThreadSafeTimedCache(TimedCache[K, V]):
    """A thread safe implementation of TimedCache"""

    def __init__(self):
        super().__init__()
        self._lock = Lock()

    def get_or_fetch(self, key: K, fetch_func: Callable[[], V], max_age: timedelta) -> V:
        with self._lock:
            return super().get_or_fetch(key, fetch_func, max_age)

    def invalidate(self, key: K) -> None:
        with self._lock:
            super().invalidate(key)

    def clear(self) -> None:
        with self._lock:
            super().clear()
