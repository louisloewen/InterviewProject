# Security

This document maps the security measures implemented in the Employee Aggregator
proxy (BFF) to the [OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0x00-header/),
and records the conscious trade-offs made for this take-home.

## Threat model in one line

The proxy is a **Backend-for-Frontend**: it is the single place that holds the
three providers' credentials and the single authentication choke point. The
frontend never sees provider secrets, and every data request flows through one
authenticated, rate-limited, input-validated entrypoint.

## OWASP API Security Top 10 — coverage

| Risk | Measure implemented | Where |
|------|--------------------|-------|
| **API1 — Broken Object Level Authorization** | A valid JWT is required on the data endpoints (`/employees`, `/departments`); the dependency runs before any handler logic | `security/auth.py`, `routes/employees.py` |
| **API2 — Broken Authentication** | Signed JWT with `sub`/`iat`/`exp`; short expiry; **rate-limited login** (5/min) to blunt brute force; secret from env, not hardcoded; generic login error (no user/pass enumeration) | `security/auth.py`, `routes/auth.py`, `security/rate_limit.py` |
| **API4 — Unrestricted Resource Consumption** | SlowAPI rate limiting on **all** endpoints (60/min default) via middleware; in-memory TTL cache also caps upstream load | `security/rate_limit.py`, `main.py`, `services/cache.py` |
| **API7 — Security Misconfiguration** | Global exception handler returns a sanitized `{"error","code"}` shape; no stack traces, provider URLs, or internals in responses; full detail logged server-side only | `security/errors.py` |
| **API8 — Lack of protection from automated threats / Improper input validation** | All query params validated by Pydantic/FastAPI (`page`/`per_page` bounds, `status` enum → 422); rate limiting throttles automation | `routes/employees.py`, `models.py`, `security/rate_limit.py` |
| **API9 — Improper Inventory / Insufficient logging** | Security logger records auth failures (username + IP, **never** password), rate-limit violations, and provider connectivity failures, with timestamps + severity | `security/logging_config.py`, `routes/auth.py`, `providers/*.py`, `security/errors.py` |

## Measures in detail

### JWT authentication (API1, API2)
- `POST /auth/login` validates demo credentials and returns a signed JWT
  (`sub`, `iat`, `exp`). Protected routes require `Authorization: Bearer <token>`.
- The signing secret is read from the `JWT_SECRET` environment variable; the dev
  fallback is ≥32 bytes (HMAC-SHA256 minimum) but is **not** for production.
- Missing/invalid/expired tokens all return **401** (we use
  `HTTPBearer(auto_error=False)` so "no token" is 401, not FastAPI's default 403).
- The login error message is intentionally generic ("Invalid username or
  password") to avoid username/password enumeration.

### Rate limiting (API4, API2)
- A global **60/min per-IP** limit applies to every endpoint via
  `SlowAPIMiddleware`; `/auth/login` adds a stricter **5/min** cap.
- Exceeding a limit returns **429** in the structured error shape and is logged.
- Limits are env-overridable (`RATE_LIMIT_DEFAULT`, `RATE_LIMIT_LOGIN`).

### Error sanitization (API7)
- Unhandled exceptions return `{"error":"Internal server error","code":"INTERNAL_ERROR"}`
  with HTTP 500 — no stack trace, provider URL, or internal detail in the body.
- `HTTPException`s are normalized to the same `{"error","code"}` shape.
- Full error detail (including which provider/URL failed) is logged server-side.

### Input validation (API8)
- Pydantic/FastAPI validate every input: `page ≥ 1`, `1 ≤ per_page ≤ 100`, and
  `status` against an enum. Invalid values return **422** before any handler runs.

### Security logging (API9)
- A dedicated `security` logger (timestamped, leveled) records:
  - failed login attempts — **username + source IP, never the password**;
  - rate-limit violations — source IP + path;
  - provider connectivity failures — provider + error detail.

## Conscious trade-offs (not accidental gaps)

- **Frontend stores the JWT in `localStorage`.** This survives page reloads
  (better UX, no bounce-to-login on refresh) at the cost of **XSS exposure** — any
  injected script can read `localStorage`, whereas an `httpOnly` cookie could not.
  Safer alternatives: `httpOnly` cookie (immune to JS reads, but needs CSRF
  defenses) or in-memory storage (no XSS persistence, but lost on refresh). Chosen
  deliberately for this take-home's UX.
- **422 validation errors keep FastAPI's default field-level shape** rather than
  the unified `{"error","code"}`. Those messages are useful client feedback and
  are not an internal leak. This is a **conscious decision**, not an inconsistency.
- **In-memory rate-limit storage** is per-process — correct for a single instance
  only. A multi-instance deployment would need shared storage (e.g. Redis), which
  is out of scope here.
- **Demo credentials, no user store / password hashing.** `admin/admin` is
  hardcoded per the exercise; a real system would use a user store with hashed
  passwords (e.g. argon2/bcrypt).
- **Wildcard CORS** (`allow_origins=["*"]`) is left as provided by the starter
  skeleton; a real deployment would pin allowed origins.
- **No HTTPS/transport security** is configured here; assumed terminated upstream.
