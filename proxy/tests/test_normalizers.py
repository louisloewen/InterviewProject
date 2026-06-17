"""Seam 3 — normalizer tests.

Pure-function tests on raw fixtures: no HTTP, no mocking. Each maps to an
acceptance criterion.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from normalizers.atlas import normalize_atlas
from normalizers.beacon import normalize_beacon
from normalizers.cobalt import normalize_cobalt


def _unix_ms(iso_date: str) -> int:
    dt = datetime.strptime(iso_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# --------------------------------------------------------------------------- #
# Atlas
# --------------------------------------------------------------------------- #


def test_atlas_salary_cents_to_annual_units(raw_atlas_record):
    assert normalize_atlas(raw_atlas_record).annual_salary == 780_000


@pytest.mark.parametrize(
    "raw_status,expected",
    [("ACTIVE", "active"), ("ON_LEAVE", "on_leave"), ("TERMINATED", "terminated")],
)
def test_atlas_status_mapping(raw_atlas_record, raw_status, expected):
    record = {**raw_atlas_record, "employment_status": raw_status}
    assert normalize_atlas(record).status == expected


def test_atlas_name_combination(raw_atlas_record):
    assert normalize_atlas(raw_atlas_record).name == "María Gonzalez"


def test_atlas_hire_date_passthrough(raw_atlas_record):
    assert normalize_atlas(raw_atlas_record).hire_date == "2018-05-12"


def test_atlas_email_normalized_lowercase_stripped(raw_atlas_record):
    assert normalize_atlas(raw_atlas_record).email == "maria.gonzalez.shared0001@acme.com"


# --------------------------------------------------------------------------- #
# Beacon
# --------------------------------------------------------------------------- #


def _raw_beacon(**overrides) -> dict:
    base = {
        "staff_id": 5001,
        "full_name": "Maria Gonzalez",
        "email": "MARIA.GONZALEZ@acme.com",
        "position": "Sr. Software Engineer",
        "team": {"id": 12, "name": "Engineering"},
        "is_active": True,
        "on_leave": False,
        "compensation": {"amount": "70000.00", "period": "monthly", "currency": "MXN"},
        "started_at": _unix_ms("2021-03-15"),
    }
    base.update(overrides)
    return base


def test_beacon_monthly_to_annual():
    # AC: float(amount) * 12 -> annual integer.
    assert normalize_beacon(_raw_beacon()).annual_salary == 840_000


@pytest.mark.parametrize(
    "is_active,on_leave,expected",
    [
        (True, False, "active"),
        (True, True, "on_leave"),
        (False, False, "terminated"),
        (False, True, "terminated"),  # is_active=False wins over on_leave
    ],
)
def test_beacon_status_from_booleans(is_active, on_leave, expected):
    record = _raw_beacon(is_active=is_active, on_leave=on_leave)
    assert normalize_beacon(record).status == expected


def test_beacon_email_lowercased():
    assert normalize_beacon(_raw_beacon()).email == "maria.gonzalez@acme.com"


def test_beacon_hire_date_from_unix_ms():
    # AC: started_at unix-ms -> ISO date.
    assert normalize_beacon(_raw_beacon()).hire_date == "2021-03-15"


def test_beacon_name_dept_role():
    emp = normalize_beacon(_raw_beacon())
    assert emp.name == "Maria Gonzalez"
    assert emp.department == "Engineering"  # team.name
    assert emp.role == "Sr. Software Engineer"  # position


# --------------------------------------------------------------------------- #
# Cobalt
# --------------------------------------------------------------------------- #


def _raw_cobalt(**overrides) -> dict:
    base = {
        "uuid": "cobalt-1",
        "name": {"given": "María", "family": "González"},
        "contact": {"email": "maria.gonzalez@acme.com ", "phone": "+52 55 1234 5678"},
        "assignment": {"role": "Software Engineer", "org_unit": "Engineering Dept"},
        "lifecycle_status": "employed",
        "pay": {"value": 840_000, "unit": "year", "iso_currency": "MXN"},
        "joined": "15/03/2021",
    }
    base.update(overrides)
    return base


def test_cobalt_date_ddmmyyyy_to_iso():
    # AC: DD/MM/YYYY -> ISO-8601.
    assert normalize_cobalt(_raw_cobalt()).hire_date == "2021-03-15"


@pytest.mark.parametrize(
    "lifecycle,expected",
    [("employed", "active"), ("on_leave", "on_leave"), ("former", "terminated")],
)
def test_cobalt_lifecycle_status(lifecycle, expected):
    record = _raw_cobalt(lifecycle_status=lifecycle)
    assert normalize_cobalt(record).status == expected


def test_cobalt_name_join():
    assert normalize_cobalt(_raw_cobalt()).name == "María González"


def test_cobalt_email_whitespace_stripped():
    assert normalize_cobalt(_raw_cobalt()).email == "maria.gonzalez@acme.com"


@pytest.mark.parametrize(
    "org_unit,expected_dept",
    [
        ("Engineering Dept", "Engineering"),
        ("Product Team", "Product"),
        ("Design Studio", "Design"),
        ("People Ops", "People"),
        ("Data", "Data"),  # already canonical -> passthrough
    ],
)
def test_cobalt_org_unit_to_department(org_unit, expected_dept):
    record = _raw_cobalt(assignment={"role": "X", "org_unit": org_unit})
    assert normalize_cobalt(record).department == expected_dept


def test_cobalt_salary_passthrough():
    # AC: pay.value is already annual whole units.
    assert normalize_cobalt(_raw_cobalt()).annual_salary == 840_000
