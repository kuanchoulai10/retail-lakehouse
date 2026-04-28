"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TagApiResponse, TagsApiResponse
from application.port.inbound.catalog.list_tags import (
    ListTagsInput,
    ListTagsUseCase,
)
from bootstrap.dependencies.use_cases import get_list_tags_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags",
    response_model=TagsApiResponse,
)
def list_tags(
    catalog: str,
    namespace: str,
    table: str,
    use_case: ListTagsUseCase = Depends(get_list_tags_use_case),
) -> TagsApiResponse:
    """Return all tags for a table."""
    result = use_case.execute(ListTagsInput(namespace=namespace, table=table))
    return TagsApiResponse(
        tags=[
            TagApiResponse(
                name=t.name,
                snapshot_id=t.snapshot_id,
                max_ref_age_ms=t.max_ref_age_ms,
            )
            for t in result.tags
        ],
    )
