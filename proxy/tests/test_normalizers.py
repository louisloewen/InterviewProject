"""Seam 3 — Atlas normalizer tests.

Pure-function tests on raw fixtures: no HTTP, no mocking. Each maps directly to
an Issue #1 acceptance criterion.
"""

from __future__ import annotations

import pytest

from normalizers.atlas import normalize_atlas


def test_salary_cents_to_annual_units(raw_atlas_record):
    # AC: annual_salary_cents -> whole annual units (÷100).
    emp = normalize_atlas(raw_atlas_record)
    assert emp.annual_salary == 780_000


@pytest.mark.parametrize(
    "raw_status,expected",
    [("ACTIVE", "active"), ("ON_LEAVE", "on_leave"), ("TERMINATED", "terminated")],
)
def test_status_mapping(raw_atlas_record, raw_status, expected):
    # AC: UPPERCASE Atlas status -> canonical lowercase enum.
    record = {**raw_atlas_record, "employment_status": raw_status}
    assert normalize_atlas(record).status == expected


def test_name_combination(raw_atlas_record):
    # AC: first_name + last_name -> single name field.
    assert normalize_atlas(raw_atlas_record).name == "María Gonzalez"


def test_hire_date_passthrough(raw_atlas_record):
    # AC: Atlas hire_date is already ISO-8601 and passes through unchanged.
    assert normalize_atlas(raw_atlas_record).hire_date == "2018-05-12"


def test_email_normalized_lowercase_stripped(raw_atlas_record):
    # Canonical rule: email lowercased and whitespace-stripped.
    assert normalize_atlas(raw_atlas_record).email == "maria.gonzalez.shared0001@acme.com"
