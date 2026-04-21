"""Define the GET /catalogs/{catalog}/namespaces endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import NamespacesResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces",
    response_model=NamespacesResponse,
)
def list_namespaces(
    catalog: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> NamespacesResponse:
    """Return all namespaces in the catalog."""
    namespaces = client.list_namespaces()
    return NamespacesResponse(namespaces=namespaces)
