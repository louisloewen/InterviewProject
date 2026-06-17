"""Atlas normalizer (Seam 3).

Pure function mapping a raw Atlas record to the canonical Employee model. No
HTTP here so it's testable on fixtures alone.
"""

from __future__ import annotations

from models import Employee

# Atlas emits UPPERCASE status enums; map them to the canonical lowercase set.
_STATUS_MAP = {
    "ACTIVE": "active",
    "ON_LEAVE": "on_leave",
    "TERMINATED": "terminated",
}


def normalize_atlas(raw: dict) -> Employee:
    """Convert one raw Atlas record into a canonical Employee."""
    return Employee(
        # Atlas splits the name; the canonical model wants one field.
        name=f"{raw['first_name']} {raw['last_name']}".strip(),
        # Canonical rule: lowercase + strip whitespace.
        email=raw["work_email"].strip().lower(),
        department=raw["department"],
        role=raw["job_title"],
        status=_STATUS_MAP[raw["employment_status"]],
        # Salary arrives as integer cents; canonical is whole annual units.
        # Cents are always multiples of 100 here, so // is exact.
        annual_salary=raw["annual_salary_cents"] // 100,
        currency=raw["currency"],
        # Atlas hire_date is already ISO-8601 — pass through.
        hire_date=raw["hire_date"],
    )
