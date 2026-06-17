"""Seam 1 — proxy API integration tests.

Drive the real FastAPI app through TestClient, with Atlas stubbed via respx so
the test is hermetic (no live providers). Exercises route -> aggregator ->
client -> normalizer -> response end to end.
"""

from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from config import settings
from main import app

TOTAL = 60


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


_ALL = [_make_record(i) for i in range(1, TOTAL + 1)]

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


def _paginate(request: httpx.Request) -> httpx.Response:
    page = int(request.url.params["page"])
    per_page = int(request.url.params["per_page"])
    start = (page - 1) * per_page
    window = _ALL[start : start + per_page]
    return httpx.Response(
        200,
        json={"data": window, "page": page, "per_page": per_page, "total": TOTAL},
    )


def _make_client() -> TestClient:
    # Stub upstream Atlas; let in-process app calls (host "testserver") through.
    respx.get(f"{settings.atlas_base_url}/v1/employees").mock(side_effect=_paginate)
    respx.route(host="testserver").pass_through()
    return TestClient(app)


@respx.mock
def test_employees_returns_paginated_metadata():
    # AC: GET /employees returns canonical employees with total/page/per_page.
    client = _make_client()
    resp = client.get("/employees?page=1&per_page=25")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == TOTAL
    assert body["page"] == 1
    assert body["per_page"] == 25
    assert len(body["data"]) == 25
    assert set(body["data"][0]) >= CANONICAL_FIELDS


@respx.mock
def test_employees_pagination_returns_distinct_slices():
    # AC: pagination navigates; total is stable across pages.
    client = _make_client()
    page1 = client.get("/employees?page=1&per_page=25").json()
    page2 = client.get("/employees?page=2&per_page=25").json()

    assert page1["data"] != page2["data"]
    assert page2["page"] == 2
    assert page2["total"] == TOTAL
    assert len(page2["data"]) == 25
