"""Deduplication (Seam 4).

Groups canonical employees by email and merges duplicates by provider priority.
The caller passes provider groups in priority order (highest first), e.g.
``[atlas, cobalt, beacon]``.

Merge rule: the highest-priority record is the base; lower-priority providers
only fill fields the higher one left empty. Since canonical records are normally
fully populated, this reduces to "highest priority wins" — but the gap-fill keeps
it correct if a field is ever blank.
"""

from __future__ import annotations

from models import Employee

# Values treated as "missing" when deciding whether a lower-priority provider
# may fill a field.
_EMPTY = (None, "")


def deduplicate(prioritized_groups: list[list[Employee]]) -> list[Employee]:
    """Merge employees across provider groups, keyed by normalized email.

    ``prioritized_groups[0]`` is the highest-priority provider.
    """
    merged: dict[str, dict] = {}

    # Process highest priority first so it becomes the base for each email.
    for group in prioritized_groups:
        for employee in group:
            key = employee.email  # already normalized by the normalizers
            fields = employee.model_dump()
            if key not in merged:
                merged[key] = fields
                continue
            existing = merged[key]
            for field, value in fields.items():
                if existing.get(field) in _EMPTY and value not in _EMPTY:
                    existing[field] = value

    # dict preserves insertion order -> stable, highest-priority-first ordering.
    return [Employee(**fields) for fields in merged.values()]
