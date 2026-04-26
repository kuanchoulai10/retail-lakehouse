"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import BranchResponse, BranchesResponse
from application.port.inbound.catalog.list_branches import (
    ListBranchesInput,
    ListBranchesUseCase,
)
from bootstrap.dependencies.use_cases import get_list_branches_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches",
    response_model=BranchesResponse,
)
def list_branches(
    catalog: str,
    namespace: str,
    table: str,
    use_case: ListBranchesUseCase = Depends(get_list_branches_use_case),
) -> BranchesResponse:
    """Return all branches for a table."""
    result = use_case.execute(ListBranchesInput(namespace=namespace, table=table))
    return BranchesResponse(
        branches=[
            BranchResponse(
                name=b.name,
                snapshot_id=b.snapshot_id,
                max_snapshot_age_ms=b.max_snapshot_age_ms,
                max_ref_age_ms=b.max_ref_age_ms,
                min_snapshots_to_keep=b.min_snapshots_to_keep,
            )
            for b in result.branches
        ],
    )
