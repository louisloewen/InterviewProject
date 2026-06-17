"""In-memory TTL cache.

Single in-process store so the expensive aggregation pipeline runs only on a
cache miss. The clock is injectable so expiry is testable without sleeping.
"""

from __future__ import annotations

import time
from typing import Any, Callable


class TTLCache:
    """A tiny key/value cache where entries expire after ``ttl_seconds``."""

    def __init__(
        self,
        ttl_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        # key -> (stored_at, value)
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Return the cached value, or None if absent or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if self._clock() - stored_at > self._ttl:
            # Lazily evict on read; no background sweeper needed.
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (self._clock(), value)

    def clear(self) -> None:
        self._store.clear()
