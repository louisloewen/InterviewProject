"""Search / filter / stats unit tests (pure functions, no HTTP)."""

from __future__ import annotations

from models import Employee
from services.filtering import compute_stats, filter_employees


def _emp(name: str, email: str, *, status: str = "active", department: str = "Engineering") -> Employee:
    return Employee(
        name=name,
        email=email,
        department=department,
        role="Engineer",
        status=status,
        annual_salary=100,
        currency="MXN",
        hire_date="2020-01-01",
    )


_PEOPLE = [
    _emp("María González", "maria.gonzalez@acme.com", status="active", department="Engineering"),
    _emp("James Smith", "james.smith@acme.com", status="on_leave", department="Product"),
    _emp("Mario Rossi", "mario.rossi@acme.com", status="terminated", department="Engineering"),
    _emp("Bob Jones", "developer42@acme.com", status="active", department="Design"),
]


def test_search_matches_name_only():
    # "jones" is in the name but not the email.
    result = filter_employees(_PEOPLE, search="jones")
    assert [e.name for e in result] == ["Bob Jones"]


def test_search_matches_email_only():
    # "developer" is in the email but not the name.
    result = filter_employees(_PEOPLE, search="developer")
    assert [e.name for e in result] == ["Bob Jones"]


def test_search_is_case_insensitive():
    result = filter_employees(_PEOPLE, search="MARIA")  # matches maria.gonzalez via email
    assert {e.email for e in result} == {"maria.gonzalez@acme.com"}


def test_status_filter_exact():
    result = filter_employees(_PEOPLE, status="on_leave")
    assert [e.name for e in result] == ["James Smith"]


def test_department_filter_exact():
    result = filter_employees(_PEOPLE, department="Engineering")
    assert {e.name for e in result} == {"María González", "Mario Rossi"}


def test_filters_compose_with_and():
    result = filter_employees(
        _PEOPLE, search="mar", status="active", department="Engineering"
    )
    assert {e.name for e in result} == {"María González"}


def test_no_match_returns_empty():
    assert filter_employees(_PEOPLE, search="zzzzz") == []


def test_compute_stats_counts_by_status():
    stats = compute_stats(_PEOPLE)
    assert (stats.active, stats.on_leave, stats.terminated) == (2, 1, 1)
