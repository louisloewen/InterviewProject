"""Issue #5 — OWASP hardening: rate limiting, error sanitization, security logging."""

from __future__ import annotations

import logging

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import routes.employees as employees_route
from main import app
from security.auth import create_access_token
from security.rate_limit import limiter, reset_rate_limiter

_AUTH = {"Authorization": f"Bearer {create_access_token('admin')}"}


def _enable_fresh_limiter() -> None:
    """Turn the limiter on with empty counters for an isolated rate-limit test."""
    reset_rate_limiter()
    limiter.enabled = True


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #


def test_login_blocked_after_5_attempts():
    _enable_fresh_limiter()
    client = TestClient(app)
    codes = [
        client.post("/auth/login", json={"username": "admin", "password": "wrong"}).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [401, 401, 401, 401, 401]
    assert codes[5] == 429  # 6th attempt exceeds the 5/min login limit


def test_rate_limit_429_is_structured():
    _enable_fresh_limiter()
    client = TestClient(app)
    last = None
    for _ in range(7):
        last = client.post("/auth/login", json={"username": "admin", "password": "x"})
    assert last.status_code == 429
    body = last.json()
    assert body["code"] == "RATE_LIMITED"
    assert "error" in body


def test_general_endpoint_is_rate_limited_but_looser_than_login():
    _enable_fresh_limiter()
    client = TestClient(app)
    # More than the login cap (5) still passes under the general 60/min limit.
    assert all(client.get("/health").status_code == 200 for _ in range(6))
    # ...and the general limit does eventually trigger a 429.
    saw_429 = False
    for _ in range(70):
        if client.get("/health").status_code == 429:
            saw_429 = True
            break
    assert saw_429


# --------------------------------------------------------------------------- #
# Error sanitization (no internal leaks)
# --------------------------------------------------------------------------- #


def test_unhandled_exception_returns_sanitized_500(monkeypatch):
    async def boom():
        raise RuntimeError("provider http://localhost:9001 leaked secret")

    # The route imports get_all_employees into its own namespace.
    monkeypatch.setattr(employees_route, "get_all_employees", boom)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/employees", headers=_AUTH)

    assert resp.status_code == 500
    assert resp.json() == {"error": "Internal server error", "code": "INTERNAL_ERROR"}
    # No internal detail leaks into the body.
    assert "localhost:9001" not in resp.text
    assert "leaked secret" not in resp.text
    assert "Traceback" not in resp.text


def test_http_exception_uses_structured_shape():
    client = TestClient(app)
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    body = resp.json()
    assert "error" in body
    assert "code" in body


# --------------------------------------------------------------------------- #
# Security logging
# --------------------------------------------------------------------------- #


def test_failed_login_logged_without_password(caplog):
    client = TestClient(app)
    with caplog.at_level(logging.WARNING, logger="security"):
        client.post("/auth/login", json={"username": "admin", "password": "supersecret"})
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "admin" in messages
    assert "supersecret" not in messages  # never log the password


def test_rate_limit_violation_logged(caplog):
    _enable_fresh_limiter()
    client = TestClient(app)
    with caplog.at_level(logging.WARNING, logger="security"):
        for _ in range(7):
            client.post("/auth/login", json={"username": "admin", "password": "x"})
    messages = " ".join(r.getMessage() for r in caplog.records).lower()
    assert "rate limit" in messages


@respx.mock
async def test_provider_fetch_failure_logged(caplog):
    from providers.atlas import fetch_atlas_employees

    respx.get("http://atlas.test/v1/employees").mock(return_value=httpx.Response(500))
    with caplog.at_level(logging.ERROR, logger="security"):
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_atlas_employees(base_url="http://atlas.test", api_key="k")
    messages = " ".join(r.getMessage() for r in caplog.records).lower()
    assert "atlas" in messages
