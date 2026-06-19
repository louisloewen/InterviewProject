"""Employees route (Seam 1).

Thin handler: validate query params, ask the service layer for the canonical
list, apply search/filters, compute stats, slice the requested page, and return
it with metadata.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from models import EmployeePage, StatusFilter
from security.auth import get_current_user
from services.aggregator import get_all_employees
from services.filtering import compute_stats, filter_employees

router = APIRouter()


# Protected: a valid Bearer token is required (Issue #3). The dependency runs
# before the handler, so unauthenticated requests never hit the providers.
@router.get(
    "/employees",
    response_model=EmployeePage,
    dependencies=[Depends(get_current_user)],
)
async def list_employees(
    page: int = Query(1, ge=1, description="1-based page number"),
    per_page: int = Query(25, ge=1, le=100, description="Page size"),
    search: str | None = Query(None, description="Case-insensitive match on name or email"),
    status: StatusFilter | None = Query(None, description="Exact status match"),
    department: str | None = Query(None, description="Exact department match"),
) -> EmployeePage:
    """Return a paginated, filtered page of canonical employees.

    Filtering is applied to the aggregated canonical list *before* pagination, so
    `total` and `stats` reflect the filtered set across all pages.
    """
    employees = await get_all_employees()
    filtered = filter_employees(
        employees,
        search=search,
        status=status.value if status else None,
        department=department,
    )
    total = len(filtered)
    stats = compute_stats(filtered)
    start = (page - 1) * per_page
    window = filtered[start : start + per_page]
    return EmployeePage(data=window, total=total, page=page, per_page=per_page, stats=stats)


@router.get("/departments", dependencies=[Depends(get_current_user)])
async def list_departments() -> list[str]:
    """Distinct department names over the full deduped set (for the filter dropdown).

    Not affected by query filters — the dropdown must list every department
    regardless of the current view.
    """
    employees = await get_all_employees()
    return sorted({e.department for e in employees})
