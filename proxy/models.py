"""Canonical data models.

The ``Employee`` model is the single shape the frontend sees, regardless of
which provider a record came from. ``EmployeePage`` is the paginated envelope
returned by ``GET /employees``.
"""

from __future__ import annotations

from pydantic import BaseModel


class Employee(BaseModel):
    """Canonical employee record (provider-agnostic).

    ``status`` is kept a plain ``str`` for now; the strict enum + 422 validation
    arrives with the filter work in Issue #4, where rejecting unknown values is
    actually desirable.
    """

    name: str
    email: str  # normalized: lowercase, whitespace-stripped
    department: str
    role: str
    status: str  # "active" | "on_leave" | "terminated"
    annual_salary: int  # whole currency units per year
    currency: str
    hire_date: str  # ISO-8601 (YYYY-MM-DD)


class EmployeePage(BaseModel):
    """Paginated response envelope for the employees endpoint."""

    data: list[Employee]
    total: int  # total matching records (full set in Issue #1)
    page: int
    per_page: int
