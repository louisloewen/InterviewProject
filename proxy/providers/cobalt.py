"""Cobalt Directory client (Seam 2).

Authenticates with a Bearer token and traverses cursor-based pagination over
``POST /api/directory/search`` until the cursor is null. Returns raw records.
"""

from __future__ import annotations

import httpx

# Request the max page size to minimize round-trips while still exercising the
# cursor loop. Injectable so tests can force multi-page traversal.
COBALT_PAGE_SIZE = 100

_TIMEOUT = httpx.Timeout(10.0)


async def fetch_cobalt_people(
    *,
    base_url: str,
    token: str,
    client: httpx.AsyncClient | None = None,
    page_size: int = COBALT_PAGE_SIZE,
) -> list[dict]:
    """Fetch every Cobalt person, following the cursor to the end."""
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        records: list[dict] = []
        cursor: str | None = None
        while True:
            # Omit cursor on the first request; send it back on subsequent ones.
            body: dict = {"limit": page_size}
            if cursor is not None:
                body["cursor"] = cursor
            response = await client.post(
                f"{base_url}/api/directory/search",
                json=body,
                # Auth: Cobalt expects an Authorization: Bearer <token> header.
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
            records.extend(data["results"])

            cursor = data["cursor"]
            if cursor is None:  # null cursor => no more pages
                break
        return records
    finally:
        if owns_client:
            await client.aclose()
