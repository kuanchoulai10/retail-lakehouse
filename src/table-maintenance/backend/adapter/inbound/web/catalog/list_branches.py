"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import BranchResponse, BranchesResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches",
    response_model=BranchesResponse,
)
def list_branches(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> BranchesResponse:
    """Return all branches for a table."""
    branches = client.list_branches(namespace, table)
    return BranchesResponse(
        branches=[BranchResponse(**b) for b in branches],
    )
