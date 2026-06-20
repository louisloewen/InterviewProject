"""Structured error handling (Issue #5, OWASP API7).

All error responses use a consistent ``{"error", "code"}`` JSON shape and never
leak stack traces, provider URLs, or other internals. Full detail is logged
server-side only.

Note: FastAPI's request-validation errors (422) are intentionally left in their
default field-level shape — those messages are useful client feedback, not an
internal leak. This is a conscious choice, not an inconsistency.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from security.logging_config import get_security_logger

logger = get_security_logger()

# Map HTTP status -> stable machine-readable code.
_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    429: "RATE_LIMITED",
}


def _structured(status_code: int, error: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "code": code})


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _CODE_BY_STATUS.get(exc.status_code, "ERROR")
    return _structured(exc.status_code, str(exc.detail), code)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # OWASP API9: log the violation (who/where) for the audit trail.
    logger.warning(
        "Rate limit exceeded: ip=%s path=%s", get_remote_address(request), request.url.path
    )
    return _structured(429, "Rate limit exceeded", "RATE_LIMITED")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # OWASP API7: log full detail server-side, return a sanitized body.
    logger.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    return _structured(500, "Internal server error", "INTERNAL_ERROR")


def register_error_handlers(app: FastAPI) -> None:
    """Register handlers. RateLimitExceeded is registered explicitly so it wins
    over the HTTPException handler (it subclasses HTTPException)."""
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
