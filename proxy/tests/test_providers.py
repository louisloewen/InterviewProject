"""Seam 2 — Atlas provider client tests.

Mock HTTP with respx. Verify auth header and full pagination traversal without
touching a live provider.
"""

from __future__ import annotations

import httpx
import respx

from providers.atlas import fetch_atlas_employees

ATLAS_BASE = "http://atlas.test"


def _make_record(i: int) -> dict:
    return {
        "id": f"A-{i}",
        "first_name": "Ann",
        "last_name": f"Lee{i}",
        "work_email": f"ann.lee{i}@acme.com",
        "job_title": "Engineer",
        "department": "Engineering",
        "employment_status": "ACTIVE",
        "annual_salary_cents": 78_000_000,
        "currency": "MXN",
        "hire_date": "2020-01-01",
    }


_ALL = [_make_record(i) for i in range(1, 4)]  # 3 records total


def _paginate(request: httpx.Request) -> httpx.Response:
    """Emulate Atlas's page-based slicing from the request's query params."""
    page = int(request.url.params["page"])
    per_page = int(request.url.params["per_page"])
    start = (page - 1) * per_page
    window = _ALL[start : start + per_page]
    return httpx.Response(
        200,
        json={"data": window, "page": page, "per_page": per_page, "total": len(_ALL)},
    )


@respx.mock
async def test_atlas_client_sends_api_key_header():
    # AC: client authenticates via the X-API-Key header.
    route = respx.get(f"{ATLAS_BASE}/v1/employees").mock(side_effect=_paginate)
    await fetch_atlas_employees(base_url=ATLAS_BASE, api_key="atlas-secret-key", page_size=2)
    assert route.called
    assert route.calls.last.request.headers["X-API-Key"] == "atlas-secret-key"


@respx.mock
async def test_atlas_client_traverses_all_pages():
    # AC: client loops through every page until the full set is collected.
    respx.get(f"{ATLAS_BASE}/v1/employees").mock(side_effect=_paginate)
    records = await fetch_atlas_employees(base_url=ATLAS_BASE, api_key="k", page_size=2)
    assert [r["id"] for r in records] == ["A-1", "A-2", "A-3"]
    # 3 records at page_size=2 => 2 round-trips (not 1, not 3).
    assert respx.calls.call_count == 2
