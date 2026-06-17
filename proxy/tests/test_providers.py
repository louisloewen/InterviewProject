"""Seam 2 — provider client tests.

Mock HTTP with respx. Verify auth and pagination traversal per provider without
touching live providers.
"""

from __future__ import annotations

import json

import httpx
import respx

from providers.atlas import fetch_atlas_employees
from providers.beacon import fetch_beacon_staff
from providers.cobalt import fetch_cobalt_people

# --------------------------------------------------------------------------- #
# Atlas — X-API-Key header + page-based pagination
# --------------------------------------------------------------------------- #

ATLAS_BASE = "http://atlas.test"


def _atlas_record(i: int) -> dict:
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


_ATLAS_ALL = [_atlas_record(i) for i in range(1, 4)]  # 3 records total


def _atlas_paginate(request: httpx.Request) -> httpx.Response:
    page = int(request.url.params["page"])
    per_page = int(request.url.params["per_page"])
    start = (page - 1) * per_page
    window = _ATLAS_ALL[start : start + per_page]
    return httpx.Response(
        200,
        json={"data": window, "page": page, "per_page": per_page, "total": len(_ATLAS_ALL)},
    )


@respx.mock
async def test_atlas_client_sends_api_key_header():
    route = respx.get(f"{ATLAS_BASE}/v1/employees").mock(side_effect=_atlas_paginate)
    await fetch_atlas_employees(base_url=ATLAS_BASE, api_key="atlas-secret-key", page_size=2)
    assert route.called
    assert route.calls.last.request.headers["X-API-Key"] == "atlas-secret-key"


@respx.mock
async def test_atlas_client_traverses_all_pages():
    respx.get(f"{ATLAS_BASE}/v1/employees").mock(side_effect=_atlas_paginate)
    records = await fetch_atlas_employees(base_url=ATLAS_BASE, api_key="k", page_size=2)
    assert [r["id"] for r in records] == ["A-1", "A-2", "A-3"]
    assert respx.calls.call_count == 2  # 3 records @ page_size 2 -> 2 round-trips


# --------------------------------------------------------------------------- #
# Beacon — api_key query parameter + single full list (no pagination)
# --------------------------------------------------------------------------- #

BEACON_BASE = "http://beacon.test"
_BEACON_STAFF = [{"staff_id": 1, "full_name": "A"}, {"staff_id": 2, "full_name": "B"}]


@respx.mock
async def test_beacon_client_sends_api_key_query_param_and_returns_full_list():
    route = respx.get(f"{BEACON_BASE}/staff").mock(
        return_value=httpx.Response(200, json=_BEACON_STAFF)
    )
    staff = await fetch_beacon_staff(base_url=BEACON_BASE, api_key="beacon-key-123")
    assert route.called
    # AC: Beacon authenticates via the api_key query parameter.
    assert route.calls.last.request.url.params["api_key"] == "beacon-key-123"
    # AC: fetches the full staff list.
    assert [s["staff_id"] for s in staff] == [1, 2]


# --------------------------------------------------------------------------- #
# Cobalt — Bearer token + cursor pagination
# --------------------------------------------------------------------------- #

COBALT_BASE = "http://cobalt.test"
_COBALT_ALL = [{"uuid": f"c-{i}"} for i in range(1, 6)]  # 5 records total


def _cobalt_search(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    limit = body["limit"]
    offset = int(body["cursor"]) if body.get("cursor") else 0
    window = _COBALT_ALL[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = str(next_offset) if next_offset < len(_COBALT_ALL) else None
    return httpx.Response(200, json={"results": window, "cursor": next_cursor})


@respx.mock
async def test_cobalt_client_sends_bearer_and_traverses_cursor():
    respx.post(f"{COBALT_BASE}/api/directory/search").mock(side_effect=_cobalt_search)
    people = await fetch_cobalt_people(
        base_url=COBALT_BASE, token="cobalt-bearer-token", page_size=2
    )
    # AC: cursor pagination traversed to the end.
    assert [p["uuid"] for p in people] == [f"c-{i}" for i in range(1, 6)]
    # AC: Bearer auth on every request.
    assert respx.calls.last.request.headers["Authorization"] == "Bearer cobalt-bearer-token"
    # 5 records @ page_size 2 -> 3 requests (2, 2, 1).
    assert respx.calls.call_count == 3
