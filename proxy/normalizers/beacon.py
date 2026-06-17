"""Beacon normalizer (Seam 3).

Pure function mapping a raw Beacon record to the canonical Employee model.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import Employee


def _status(is_active: bool, on_leave: bool) -> str:
    # Order matters: a terminated person (is_active=False) is terminated even if
    # an on_leave flag lingers. Check termination first, then leave, else active.
    if not is_active:
        return "terminated"
    if on_leave:
        return "on_leave"
    return "active"


def _hire_date(started_at_ms: int) -> str:
    # started_at is unix milliseconds (UTC); render as an ISO date.
    dt = datetime.fromtimestamp(started_at_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def normalize_beacon(raw: dict) -> Employee:
    """Convert one raw Beacon record into a canonical Employee."""
    comp = raw["compensation"]
    return Employee(
        # full_name is already combined.
        name=raw["full_name"],
        # Beacon emails vary in case; canonical rule: lowercase + strip.
        email=raw["email"].strip().lower(),
        department=raw["team"]["name"],
        role=raw["position"],
        status=_status(raw["is_active"], raw["on_leave"]),
        # Monthly decimal string -> annual whole units.
        annual_salary=int(round(float(comp["amount"]) * 12)),
        currency=comp["currency"],
        hire_date=_hire_date(raw["started_at"]),
    )
