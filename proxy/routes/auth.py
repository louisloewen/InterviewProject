"""Auth route (Issue #3 + #5).

POST /auth/login: validate demo credentials, return a signed JWT. Rate-limited
(OWASP API2) and failed attempts are logged (OWASP API9).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from slowapi.util import get_remote_address

from config import settings
from security.auth import authenticate, create_access_token
from security.logging_config import get_security_logger
from security.rate_limit import limiter

router = APIRouter()
logger = get_security_logger()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Stricter rate limit than the global default to blunt credential brute-forcing
# (OWASP API2). The `request: Request` param is required by SlowAPI's decorator.
@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_login)
def login(request: Request, body: LoginRequest) -> TokenResponse:
    """Exchange demo credentials for a JWT."""
    if not authenticate(body.username, body.password):
        # OWASP API9: log the username + source IP, never the password.
        logger.warning(
            "Failed login attempt: username=%r ip=%s",
            body.username,
            get_remote_address(request),
        )
        # Generic message: don't reveal whether the username or password was wrong.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)
