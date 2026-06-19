"""Auth route (Issue #3).

POST /auth/login: validate demo credentials, return a signed JWT.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from security.auth import authenticate, create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """Exchange demo credentials for a JWT."""
    if not authenticate(body.username, body.password):
        # Generic message: don't reveal whether the username or password was wrong.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)
