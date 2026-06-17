"""In-memory TTL cache tests.

An injectable clock lets us test expiry deterministically (no sleeping).
"""

from __future__ import annotations

from services.cache import TTLCache


class _Clock:
    """Manually advanceable monotonic clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_returns_stored_value_within_ttl():
    clock = _Clock()
    cache = TTLCache(ttl_seconds=60, clock=clock)
    cache.set("k", [1, 2, 3])
    assert cache.get("k") == [1, 2, 3]
    clock.now = 59  # still inside the window
    assert cache.get("k") == [1, 2, 3]


def test_value_expires_after_ttl():
    clock = _Clock()
    cache = TTLCache(ttl_seconds=60, clock=clock)
    cache.set("k", "v")
    clock.now = 61  # past TTL
    assert cache.get("k") is None


def test_missing_key_returns_none():
    assert TTLCache(ttl_seconds=60).get("absent") is None


def test_clear_evicts_everything():
    cache = TTLCache(ttl_seconds=60)
    cache.set("k", "v")
    cache.clear()
    assert cache.get("k") is None
