"""Employees route (Seam 1).

Thin handler: validate pagination params, ask the service layer for the canonical
list, slice the requested page, and return it with metadata.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from models import EmployeePage
from security.auth import get_current_user
from services.aggregator import get_all_employees

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
) -> EmployeePage:
    """Return a paginated page of canonical employees.

    Pagination is applied over the *aggregated* canonical list (not by proxying
    Atlas's own page params), because Issue #2 will merge multiple providers and
    dedup before paging.
    """
    employees = await get_all_employees()
    total = len(employees)
    start = (page - 1) * per_page
    window = employees[start : start + per_page]
    return EmployeePage(data=window, total=total, page=page, per_page=per_page)
