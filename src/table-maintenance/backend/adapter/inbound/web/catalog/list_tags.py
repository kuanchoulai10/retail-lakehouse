"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TagResponse, TagsResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags",
    response_model=TagsResponse,
)
def list_tags(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> TagsResponse:
    """Return all tags for a table."""
    tags = client.list_tags(namespace, table)
    return TagsResponse(
        tags=[TagResponse(**t) for t in tags],
    )
