"""Aggregation pipeline.

Issue #1: fetch Atlas, normalize to canonical employees. Concurrent multi-provider
fetch, dedup, and TTL caching arrive in Issue #2.
"""

from __future__ import annotations

from config import settings
from models import Employee
from normalizers.atlas import normalize_atlas
from providers.atlas import fetch_atlas_employees


async def get_all_employees() -> list[Employee]:
    """Fetch all Atlas records and return them as canonical employees."""
    raw_records = await fetch_atlas_employees(
        base_url=settings.atlas_base_url,
        api_key=settings.atlas_api_key,
    )
    return [normalize_atlas(record) for record in raw_records]
