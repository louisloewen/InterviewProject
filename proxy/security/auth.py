"""JWT authentication (Issue #3).

Token issuance/verification and the FastAPI dependency that protects routes.

Security notes:
- The signing secret comes from config (env var ``JWT_SECRET``), never hardcoded.
- Tokens are short-lived (``exp``) so a leaked token stops working.
- Demo credentials only (admin/admin); no user store or password hashing — out of
  scope per the PRD.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

# Hardcoded demo credentials (PRD: no real user management).
_DEMO_USERNAME = "admin"
_DEMO_PASSWORD = "admin"


def authenticate(username: str, password: str) -> bool:
    """Validate credentials against the demo user."""
    return username == _DEMO_USERNAME and password == _DEMO_PASSWORD


def create_access_token(subject: str, *, expires_minutes: int | None = None) -> str:
    """Sign a JWT for ``subject`` with iat/exp claims.

    ``expires_minutes`` overrides the configured lifetime — used by tests to mint
    an already-expired token (negative value) without waiting real time.
    """
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode/verify a JWT. Raises jwt exceptions on invalid/expired tokens."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# auto_error=False: the default HTTPBearer returns 403 when the header is missing,
# but we want a consistent 401 for "no token" as well as invalid/expired tokens.
_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Dependency that requires a valid Bearer token; returns the subject."""
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token")
    return payload["sub"]
