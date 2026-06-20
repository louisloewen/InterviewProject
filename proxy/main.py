"""Proxy (BFF) — application entrypoint.

Fetches employees from three Provider APIs, normalizes + deduplicates them, and
exposes a paginated, searchable, JWT-protected API to the frontend. Security
hardening (rate limiting, sanitized errors, security logging) lives in
``security/`` and is wired up here.

Run:  uv run uvicorn main:app --port 8000 --reload
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from routes.auth import router as auth_router
from routes.employees import router as employees_router
from security.errors import register_error_handlers
from security.logging_config import configure_logging
from security.rate_limit import limiter

configure_logging()

app = FastAPI(title="Employee Aggregator Proxy")

# Rate limiting (OWASP API4): default limit applies to every endpoint via the
# middleware; /auth/login adds a stricter cap. Handlers below return 429s in the
# structured error shape.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Structured, sanitized error responses (OWASP API7) + security logging (API9).
register_error_handlers(app)

# Open CORS for local frontend dev — added last so it wraps all responses
# (including 429/500). Not part of the exercise, leave as-is.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Auth (Issue #3): /auth/login is public; /employees is protected by the
# get_current_user dependency on its route. /health stays unauthenticated.
app.include_router(auth_router)
app.include_router(employees_router)
