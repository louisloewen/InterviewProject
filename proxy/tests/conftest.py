"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


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
