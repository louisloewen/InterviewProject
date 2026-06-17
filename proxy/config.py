"""Application configuration.

Loads environment variables from the repo-root ``.env`` via python-dotenv and
exposes them as a single typed ``Settings`` object.

Why centralize: provider clients, JWT auth, and the cache should never read
``os.environ`` directly. Funnelling all env access through one module keeps
secrets out of business logic, makes every consumer trivially testable
(inject a Settings), and gives one obvious place to see what the proxy needs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# .env lives at the repo root, one level above proxy/. load_dotenv is a no-op if
# the file is missing, so environments that inject real env vars (CI/prod) keep
# working without a .env on disk.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Typed, immutable view of the proxy's runtime configuration."""

    # Upstream provider credentials. The BFF holds these and never exposes them
    # to the frontend (the whole point of the proxy pattern).
    atlas_api_key: str
    beacon_api_key: str
    cobalt_token: str

    # Upstream provider base URLs. Defaulted to the local mock ports but kept in
    # config so clients never hardcode a host — swappable per environment/test.
    atlas_base_url: str
    beacon_base_url: str
    cobalt_base_url: str

    # JWT signing config (Issue #3). Secret defaults to a dev-only value so the
    # app boots out of the box; override via .env for anything real.
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    # Aggregation cache TTL in seconds (Issue #2).
    cache_ttl_seconds: int


def get_settings() -> Settings:
    """Build a Settings snapshot from the current environment."""
    return Settings(
        atlas_api_key=os.getenv("ATLAS_API_KEY", ""),
        beacon_api_key=os.getenv("BEACON_API_KEY", ""),
        cobalt_token=os.getenv("COBALT_TOKEN", ""),
        atlas_base_url=os.getenv("ATLAS_BASE_URL", "http://localhost:9001"),
        beacon_base_url=os.getenv("BEACON_BASE_URL", "http://localhost:9002"),
        cobalt_base_url=os.getenv("COBALT_BASE_URL", "http://localhost:9003"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-insecure-change-me"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "60")),
    )


# Module-level singleton for convenient imports: ``from config import settings``.
settings = get_settings()
