"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.adapter.inbound.web.catalog.dto import SnapshotResponse, SnapshotsResponse
from core.application.port.inbound.catalog.list_snapshots import (
    ListSnapshotsInput,
    ListSnapshotsUseCase,
)
from api.dependencies.use_cases import get_list_snapshots_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots",
    response_model=SnapshotsResponse,
)
def list_snapshots(
    catalog: str,
    namespace: str,
    table: str,
    use_case: ListSnapshotsUseCase = Depends(get_list_snapshots_use_case),
) -> SnapshotsResponse:
    """Return all snapshots for a table."""
    result = use_case.execute(ListSnapshotsInput(namespace=namespace, table=table))
    return SnapshotsResponse(
        snapshots=[
            SnapshotResponse(
                snapshot_id=s.snapshot_id,
                parent_id=s.parent_id,
                timestamp_ms=s.timestamp_ms,
                summary=s.summary,
            )
            for s in result.snapshots
        ],
    )
