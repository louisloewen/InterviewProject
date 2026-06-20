"""Security logging setup (Issue #5, OWASP API9).

A single named "security" logger records auth failures, rate-limit violations,
and provider connectivity issues with timestamps and severity — the audit trail
for security-relevant events.
"""

from __future__ import annotations

import logging

SECURITY_LOGGER = "security"


def configure_logging() -> None:
    """Initialize root logging (timestamped, leveled). Idempotent-ish via force."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_security_logger() -> logging.Logger:
    return logging.getLogger(SECURITY_LOGGER)
