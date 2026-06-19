"""Search / filter / stats over the canonical employee list.

Pure functions (no HTTP, no I/O) so they're unit-testable on plain lists. The
route applies these *before* pagination so `total` and the page window reflect
the filtered set.
"""

from __future__ import annotations

from models import Employee, EmployeeStats


def filter_employees(
    employees: list[Employee],
    *,
    search: str | None = None,
    status: str | None = None,
    department: str | None = None,
) -> list[Employee]:
    """Return employees matching all provided filters (AND semantics)."""
    result = employees

    if search:
        needle = search.lower()
        result = [
            e for e in result if needle in e.name.lower() or needle in e.email.lower()
        ]
    if status:
        result = [e for e in result if e.status == status]
    if department:
        result = [e for e in result if e.department == department]

    return result


def compute_stats(employees: list[Employee]) -> EmployeeStats:
    """Count employees by status over the given (already-filtered) list."""
    return EmployeeStats(
        active=sum(1 for e in employees if e.status == "active"),
        on_leave=sum(1 for e in employees if e.status == "on_leave"),
        terminated=sum(1 for e in employees if e.status == "terminated"),
    )
