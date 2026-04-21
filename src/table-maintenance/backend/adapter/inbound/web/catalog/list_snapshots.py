"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import SnapshotResponse, SnapshotsResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots",
    response_model=SnapshotsResponse,
)
def list_snapshots(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> SnapshotsResponse:
    """Return all snapshots for a table."""
    snapshots = client.list_snapshots(namespace, table)
    return SnapshotsResponse(
        snapshots=[SnapshotResponse(**s) for s in snapshots],
    )
