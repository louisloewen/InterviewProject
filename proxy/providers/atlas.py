"""Atlas HR client (Seam 2).

Authenticates with the ``X-API-Key`` header and traverses Atlas's page-based
pagination, returning the full list of raw records. No normalization here.
"""

from __future__ import annotations

import httpx

from security.logging_config import get_security_logger

logger = get_security_logger()

# Atlas defaults to per_page=2 (to force pagination handling). We request the
# max page size to minimize round-trips (~12 requests for ~1,200 records instead
# of ~600) while still exercising the traversal loop.
ATLAS_PAGE_SIZE = 100

# Bound each request so a hung provider can't stall the whole aggregation.
_TIMEOUT = httpx.Timeout(10.0)


async def fetch_atlas_employees(
    *,
    base_url: str,
    api_key: str,
    client: httpx.AsyncClient | None = None,
    page_size: int = ATLAS_PAGE_SIZE,
) -> list[dict]:
    """Fetch every Atlas employee, following pagination to the end.

    ``client`` is injectable so callers can share a connection pool; when absent
    we create and close our own. ``page_size`` is exposed mainly so tests can
    force multi-page traversal with tiny pages.
    """
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        records: list[dict] = []
        page = 1
        while True:
            try:
                response = await client.get(
                    f"{base_url}/v1/employees",
                    params={"page": page, "per_page": page_size},
                    # Auth: Atlas expects the key in the X-API-Key header.
                    headers={"X-API-Key": api_key},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                # OWASP API9: log provider connectivity issues; the generic
                # handler sanitizes the client-facing response (API7).
                logger.error("Atlas provider fetch failed (page %s): %s", page, exc)
                raise
            body = response.json()
            records.extend(body["data"])

            # Stop once we've requested through the last page (PRD's rule).
            if page * page_size >= body["total"]:
                break
            page += 1
        return records
    finally:
        if owns_client:
            await client.aclose()
