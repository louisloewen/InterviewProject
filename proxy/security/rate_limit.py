"""Rate limiting (Issue #5, OWASP API4 / API2).

SlowAPI limiter keyed by client IP. A general default limit applies to every
endpoint (via SlowAPIMiddleware in main); /auth/login adds a stricter cap to
blunt credential brute-forcing. Limits come from config (env-overridable).

Note: the default in-memory storage is per-process — correct for a single
instance only. A multi-instance deployment would need shared storage (e.g.
Redis), which is out of scope here (documented in SECURITY.md).
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
)


def reset_rate_limiter() -> None:
    """Clear all counters (used by tests to isolate rate-limit cases)."""
    limiter.reset()
