"""Seam 4 — deduplication tests.

Synthetic canonical records make priority assertions crisp. Email is the dedup
key and is already normalized by the normalizers.

deduplicate() takes provider groups in priority order: [atlas, cobalt, beacon].
"""

from __future__ import annotations

from models import Employee
from services.dedup import deduplicate


def _emp(
    email: str,
    *,
    name: str = "X",
    role: str = "Role",
    status: str = "active",
    department: str = "Engineering",
    annual_salary: int = 100,
    currency: str = "MXN",
    hire_date: str = "2020-01-01",
) -> Employee:
    return Employee(
        name=name,
        email=email,
        department=department,
        role=role,
        status=status,
        annual_salary=annual_salary,
        currency=currency,
        hire_date=hire_date,
    )


def test_all_three_overlap_merges_to_one_atlas_wins():
    # María in all three providers -> 1 record, Atlas fields win.
    atlas = [_emp("maria.gonzalez@acme.com", name="María González", role="Software Engineer")]
    cobalt = [_emp("maria.gonzalez@acme.com", name="Maria G", role="SE (Cobalt)")]
    beacon = [_emp("maria.gonzalez@acme.com", name="Maria B", role="Sr. Software Engineer")]

    result = deduplicate([atlas, cobalt, beacon])

    assert len(result) == 1
    assert result[0].name == "María González"  # Atlas
    assert result[0].role == "Software Engineer"  # Atlas beats Beacon's "Sr."


def test_cobalt_beats_beacon_when_no_atlas():
    # Yuki only in Beacon + Cobalt -> Cobalt wins (higher priority).
    cobalt = [_emp("yuki.tanaka@acme.com", status="active")]
    beacon = [_emp("yuki.tanaka@acme.com", status="on_leave")]

    result = deduplicate([[], cobalt, beacon])

    assert len(result) == 1
    assert result[0].status == "active"  # Cobalt, not Beacon's on_leave


def test_single_provider_record_passes_through():
    atlas = [_emp("solo@acme.com", name="Solo")]
    result = deduplicate([atlas, [], []])
    assert len(result) == 1
    assert result[0].name == "Solo"


def test_non_overlapping_records_all_kept():
    result = deduplicate(
        [[_emp("a@acme.com")], [_emp("b@acme.com")], [_emp("c@acme.com")]]
    )
    assert {r.email for r in result} == {"a@acme.com", "b@acme.com", "c@acme.com"}


def test_lower_priority_fills_empty_field():
    # Higher-priority record has an empty role; lower priority fills the gap.
    atlas = [_emp("p@acme.com", role="")]
    beacon = [_emp("p@acme.com", role="Filled")]
    result = deduplicate([atlas, [], beacon])
    assert len(result) == 1
    assert result[0].role == "Filled"
