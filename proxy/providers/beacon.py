"""Beacon People client (Seam 2).

Authenticates with the ``api_key`` query parameter and fetches the full staff
list in one call (Beacon has no pagination). Returns raw records.
"""

from __future__ import annotations

import httpx

from security.logging_config import get_security_logger

logger = get_security_logger()

_TIMEOUT = httpx.Timeout(10.0)


async def fetch_beacon_staff(
    *,
    base_url: str,
    api_key: str,
    client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Fetch the full Beacon staff list."""
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        try:
            response = await client.get(
                f"{base_url}/staff",
                # Auth: Beacon expects the key as the api_key query parameter.
                params={"api_key": api_key},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # OWASP API9: log provider connectivity issues server-side.
            logger.error("Beacon provider fetch failed: %s", exc)
            raise
        return response.json()  # bare JSON array, no envelope
    finally:
        if owns_client:
            await client.aclose()
