"""Seam 1 — JWT authentication tests.

Login issuance, protection of /employees, and that /health stays public.
Expiration is tested by minting an already-expired token (no real waiting).
"""

from __future__ import annotations

import httpx
import jwt
import pytest
import respx
from fastapi.testclient import TestClient

from main import app
from security.auth import create_access_token, decode_access_token

client = TestClient(app)


def _stub_providers_empty() -> None:
    """Stub all three providers so a protected call can reach a 200."""
    from config import settings

    respx.get(f"{settings.atlas_base_url}/v1/employees").mock(
        return_value=httpx.Response(
            200, json={"data": [], "page": 1, "per_page": 100, "total": 0}
        )
    )
    respx.get(f"{settings.beacon_base_url}/staff").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.post(f"{settings.cobalt_base_url}/api/directory/search").mock(
        return_value=httpx.Response(200, json={"results": [], "cursor": None})
    )
    respx.route(host="testserver").pass_through()


# --------------------------------------------------------------------------- #
# Token unit behaviour
# --------------------------------------------------------------------------- #


def test_token_roundtrip_has_expected_claims():
    payload = decode_access_token(create_access_token("admin"))
    assert payload["sub"] == "admin"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_token_is_rejected_by_decode():
    expired = create_access_token("admin", expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #


def test_login_valid_returns_bearer_token():
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    # token is a valid JWT for admin
    assert decode_access_token(body["access_token"])["sub"] == "admin"


def test_login_invalid_returns_401_structured():
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert isinstance(resp.json(), dict)  # structured JSON, not a bare string


# --------------------------------------------------------------------------- #
# Protection of /employees
# --------------------------------------------------------------------------- #


def test_employees_without_token_returns_401():
    # Dependency rejects before any provider call, so no stubs needed.
    resp = client.get("/employees")
    assert resp.status_code == 401


@respx.mock
def test_employees_with_valid_token_returns_200():
    _stub_providers_empty()
    token = create_access_token("admin")
    resp = client.get("/employees", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_employees_with_expired_token_returns_401():
    expired = create_access_token("admin", expires_minutes=-1)
    resp = client.get("/employees", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# /health stays public
# --------------------------------------------------------------------------- #


def test_health_remains_unauthenticated():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
