"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_aggregator_cache():
    """Reset the aggregator's module-level cache before each test.

    The cache is a singleton, so without this, results would leak between tests.
    Guarded so it's a no-op while the aggregator cache isn't implemented yet
    (keeps the red phase showing each test's real failure reason).
    """
    try:
        from services.aggregator import clear_cache

        clear_cache()
    except (ImportError, AttributeError):
        pass
    yield


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Disable rate limiting for normal tests.

    The limiter holds per-process counters that would otherwise leak across tests
    (a 60/min cap on /employees could spuriously 429 mid-suite). Tests that
    actually exercise rate limiting re-enable it and reset storage themselves.
    Guarded so it's a no-op while rate_limit isn't implemented yet.
    """
    try:
        from security.rate_limit import limiter

        limiter.enabled = False
    except (ImportError, AttributeError):
        pass
    yield


@pytest.fixture
def raw_atlas_record() -> dict:
    """One raw Atlas record shaped exactly like the mock provider emits.

    The email is intentionally mixed-case with a trailing space so the
    normalizer's lowercase+strip rule is exercised, even though real Atlas
    data happens to be clean.
    """
    return {
        "id": "A-2001",
        "first_name": "María",
        "last_name": "Gonzalez",
        "work_email": "Maria.Gonzalez.shared0001@acme.com ",
        "job_title": "Software Engineer",
        "department": "Engineering",
        "employment_status": "ACTIVE",
        "annual_salary_cents": 78_000_000,  # -> 780000 whole units
        "currency": "MXN",
        "hire_date": "2018-05-12",
    }
