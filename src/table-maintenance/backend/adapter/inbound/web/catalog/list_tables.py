"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TablesResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables",
    response_model=TablesResponse,
)
def list_tables(
    catalog: str,
    namespace: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> TablesResponse:
    """Return all tables in the namespace."""
    tables = client.list_tables(namespace)
    return TablesResponse(tables=tables)
