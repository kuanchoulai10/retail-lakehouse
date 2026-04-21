"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import (
    SchemaFieldResponse,
    SchemaResponse,
    TableDetailResponse,
)
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}",
    response_model=TableDetailResponse,
)
def get_table(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> TableDetailResponse:
    """Return metadata for a specific table."""
    data = client.get_table(namespace, table)
    return TableDetailResponse(
        table=data["table"],
        namespace=data["namespace"],
        location=data["location"],
        current_snapshot_id=data["current_snapshot_id"],
        schema=SchemaResponse(
            fields=[SchemaFieldResponse(**f) for f in data["schema"]["fields"]],
        ),
        properties=data["properties"],
    )
