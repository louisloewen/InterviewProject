"""Cobalt normalizer (Seam 3).

Pure function mapping a raw Cobalt record to the canonical Employee model.
"""

from __future__ import annotations

from models import Employee

# Cobalt lifecycle states -> canonical status.
_STATUS_MAP = {
    "employed": "active",
    "on_leave": "on_leave",
    "former": "terminated",
}

# Cobalt org_unit labels -> canonical department names. Only the labels that
# differ need an entry; everything else already matches and passes through.
_DEPARTMENT_MAP = {
    "Engineering Dept": "Engineering",
    "Product Team": "Product",
    "Design Studio": "Design",
    "People Ops": "People",
}


def _hire_date(joined: str) -> str:
    # DD/MM/YYYY -> ISO-8601 (YYYY-MM-DD).
    day, month, year = joined.split("/")
    return f"{year}-{month}-{day}"


def normalize_cobalt(raw: dict) -> Employee:
    """Convert one raw Cobalt record into a canonical Employee."""
    name = raw["name"]
    assignment = raw["assignment"]
    pay = raw["pay"]
    org_unit = assignment["org_unit"]
    return Employee(
        name=f"{name['given']} {name['family']}".strip(),
        # contact.email sometimes has stray whitespace; strip + lowercase.
        email=raw["contact"]["email"].strip().lower(),
        department=_DEPARTMENT_MAP.get(org_unit, org_unit),
        role=assignment["role"],
        status=_STATUS_MAP[raw["lifecycle_status"]],
        # pay.value is already annual whole units.
        annual_salary=pay["value"],
        currency=pay["iso_currency"],
        hire_date=_hire_date(raw["joined"]),
    )
