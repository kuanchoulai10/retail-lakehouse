"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import SnapshotApiResponse, SnapshotsApiResponse
from application.port.inbound.catalog.list_snapshots import (
    ListSnapshotsUseCaseInput,
    ListSnapshotsUseCase,
)
from bootstrap.dependencies.use_cases import get_list_snapshots_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots",
    response_model=SnapshotsApiResponse,
)
def list_snapshots(
    catalog: str,
    namespace: str,
    table: str,
    use_case: ListSnapshotsUseCase = Depends(get_list_snapshots_use_case),
) -> SnapshotsApiResponse:
    """Return all snapshots for a table."""
    result = use_case.execute(
        ListSnapshotsUseCaseInput(namespace=namespace, table=table)
    )
    return SnapshotsApiResponse(
        snapshots=[
            SnapshotApiResponse(
                snapshot_id=s.snapshot_id,
                parent_id=s.parent_id,
                timestamp_ms=s.timestamp_ms,
                summary=s.summary,
            )
            for s in result.snapshots
        ],
    )
