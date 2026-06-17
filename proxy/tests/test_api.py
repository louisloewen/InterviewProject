"""Seam 1 — proxy API integration tests.

Drive the real FastAPI app through TestClient, with all three providers stubbed
via respx so the test is hermetic. Exercises route -> aggregator -> clients ->
normalizers -> dedup -> response end to end.
"""

from __future__ import annotations

import asyncio
import json
import time

import httpx
import respx
from fastapi.testclient import TestClient

import services.aggregator as aggregator
from config import settings
from main import app

CANONICAL_FIELDS = {
    "name",
    "email",
    "department",
    "role",
    "status",
    "annual_salary",
    "currency",
    "hire_date",
}

# --------------------------------------------------------------------------- #
# Raw record builders (provider-shaped) + respx responders
# --------------------------------------------------------------------------- #


def _atlas_raw(email: str, *, role: str = "Engineer") -> dict:
    return {
        "id": "A-1",
        "first_name": "Ann",
        "last_name": "Lee",
        "work_email": email,
        "job_title": role,
        "department": "Engineering",
        "employment_status": "ACTIVE",
        "annual_salary_cents": 78_000_000,
        "currency": "MXN",
        "hire_date": "2020-01-01",
    }


def _beacon_raw(email: str, *, role: str = "Engineer") -> dict:
    return {
        "staff_id": 1,
        "full_name": "Ann Lee",
        "email": email,
        "position": role,
        "team": {"id": 12, "name": "Engineering"},
        "is_active": True,
        "on_leave": False,
        "compensation": {"amount": "70000.00", "period": "monthly", "currency": "MXN"},
        "started_at": 1_577_836_800_000,  # 2020-01-01 UTC
    }


def _cobalt_raw(email: str, *, role: str = "Engineer") -> dict:
    return {
        "uuid": "c-1",
        "name": {"given": "Ann", "family": "Lee"},
        "contact": {"email": email, "phone": "x"},
        "assignment": {"role": role, "org_unit": "Engineering Dept"},
        "lifecycle_status": "employed",
        "pay": {"value": 780_000, "unit": "year", "iso_currency": "MXN"},
        "joined": "01/01/2020",
    }


def _atlas_responder(records: list[dict]):
    def responder(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        per_page = int(request.url.params["per_page"])
        start = (page - 1) * per_page
        window = records[start : start + per_page]
        return httpx.Response(
            200,
            json={"data": window, "page": page, "per_page": per_page, "total": len(records)},
        )

    return responder


def _cobalt_responder(records: list[dict]):
    def responder(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        limit = body["limit"]
        offset = int(body["cursor"]) if body.get("cursor") else 0
        window = records[offset : offset + limit]
        next_offset = offset + limit
        next_cursor = str(next_offset) if next_offset < len(records) else None
        return httpx.Response(200, json={"results": window, "cursor": next_cursor})

    return responder


def _make_client(
    atlas: list[dict] | None = None,
    beacon: list[dict] | None = None,
    cobalt: list[dict] | None = None,
) -> TestClient:
    atlas = atlas if atlas is not None else []
    beacon = beacon if beacon is not None else []
    cobalt = cobalt if cobalt is not None else []
    respx.get(f"{settings.atlas_base_url}/v1/employees").mock(side_effect=_atlas_responder(atlas))
    respx.get(f"{settings.beacon_base_url}/staff").mock(
        return_value=httpx.Response(200, json=beacon)
    )
    respx.post(f"{settings.cobalt_base_url}/api/directory/search").mock(
        side_effect=_cobalt_responder(cobalt)
    )
    respx.route(host="testserver").pass_through()
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Pagination metadata (Atlas-only datasets, distinct emails -> no dedup effect)
# --------------------------------------------------------------------------- #

_ATLAS_60 = [_atlas_raw(f"ann.lee{i}@acme.com") for i in range(1, 61)]


@respx.mock
def test_employees_returns_paginated_metadata():
    client = _make_client(atlas=_ATLAS_60)
    resp = client.get("/employees?page=1&per_page=25")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 60
    assert body["page"] == 1
    assert body["per_page"] == 25
    assert len(body["data"]) == 25
    assert set(body["data"][0]) >= CANONICAL_FIELDS


@respx.mock
def test_employees_pagination_returns_distinct_slices():
    client = _make_client(atlas=_ATLAS_60)
    page1 = client.get("/employees?page=1&per_page=25").json()
    page2 = client.get("/employees?page=2&per_page=25").json()

    assert page1["data"] != page2["data"]
    assert page2["page"] == 2
    assert page2["total"] == 60
    assert len(page2["data"]) == 25


# --------------------------------------------------------------------------- #
# Deduplication across all three providers
# --------------------------------------------------------------------------- #


@respx.mock
def test_employees_deduplicates_across_providers_atlas_priority():
    # María overlaps all 3 (varying email case/whitespace); plus 1 unique each.
    atlas = [
        _atlas_raw("maria.gonzalez@acme.com", role="Software Engineer"),
        _atlas_raw("atlas.only@acme.com"),
    ]
    beacon = [
        _beacon_raw("MARIA.GONZALEZ@acme.com", role="Sr. Software Engineer"),
        _beacon_raw("beacon.only@acme.com"),
    ]
    cobalt = [
        _cobalt_raw("maria.gonzalez@acme.com ", role="SE (Cobalt)"),
        _cobalt_raw("cobalt.only@acme.com"),
    ]
    client = _make_client(atlas=atlas, beacon=beacon, cobalt=cobalt)
    body = client.get("/employees?page=1&per_page=100").json()

    # 4 unique emails: maria (merged) + 3 unique.
    assert body["total"] == 4
    maria = next(e for e in body["data"] if e["email"] == "maria.gonzalez@acme.com")
    assert maria["role"] == "Software Engineer"  # Atlas wins


# --------------------------------------------------------------------------- #
# Concurrency: providers fetched in parallel, not serially
# --------------------------------------------------------------------------- #


async def test_providers_are_fetched_concurrently(monkeypatch):
    delay = 0.15

    async def slow(**_kwargs):
        await asyncio.sleep(delay)
        return []

    monkeypatch.setattr(aggregator, "fetch_atlas_employees", slow)
    monkeypatch.setattr(aggregator, "fetch_beacon_staff", slow)
    monkeypatch.setattr(aggregator, "fetch_cobalt_people", slow)
    aggregator.clear_cache()

    start = time.perf_counter()
    result = await aggregator.get_all_employees()
    elapsed = time.perf_counter() - start

    assert result == []
    # Concurrent ~= one delay; serial would be ~= 3 * delay.
    assert elapsed < delay * 2
