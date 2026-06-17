"""Aggregation pipeline.

Fetches all three providers concurrently, normalizes each to canonical
employees, deduplicates by email (Atlas > Cobalt > Beacon), and caches the
result in memory with a TTL so repeated requests don't re-hit the providers.
"""

from __future__ import annotations

import asyncio

from config import settings
from models import Employee
from normalizers.atlas import normalize_atlas
from normalizers.beacon import normalize_beacon
from normalizers.cobalt import normalize_cobalt
from providers.atlas import fetch_atlas_employees
from providers.beacon import fetch_beacon_staff
from providers.cobalt import fetch_cobalt_people
from services.cache import TTLCache
from services.dedup import deduplicate

_cache = TTLCache(settings.cache_ttl_seconds)
_CACHE_KEY = "all_employees"


def clear_cache() -> None:
    """Drop cached results (used by tests; handy for manual cache busting)."""
    _cache.clear()


async def get_all_employees() -> list[Employee]:
    """Return deduplicated canonical employees from all providers (cached)."""
    cached = _cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    # Fetch all three providers concurrently: total time ~= the slowest provider,
    # not the sum of all three.
    atlas_raw, beacon_raw, cobalt_raw = await asyncio.gather(
        fetch_atlas_employees(
            base_url=settings.atlas_base_url, api_key=settings.atlas_api_key
        ),
        fetch_beacon_staff(
            base_url=settings.beacon_base_url, api_key=settings.beacon_api_key
        ),
        fetch_cobalt_people(
            base_url=settings.cobalt_base_url, token=settings.cobalt_token
        ),
    )

    atlas = [normalize_atlas(r) for r in atlas_raw]
    beacon = [normalize_beacon(r) for r in beacon_raw]
    cobalt = [normalize_cobalt(r) for r in cobalt_raw]

    # Priority order: Atlas > Cobalt > Beacon.
    result = deduplicate([atlas, cobalt, beacon])

    _cache.set(_CACHE_KEY, result)
    return result
