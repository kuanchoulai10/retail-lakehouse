"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.adapter.inbound.web.catalog.dto import TagResponse, TagsResponse
from application.port.inbound.catalog.list_tags import (
    ListTagsInput,
    ListTagsUseCase,
)
from dependencies.use_cases import get_list_tags_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags",
    response_model=TagsResponse,
)
def list_tags(
    catalog: str,
    namespace: str,
    table: str,
    use_case: ListTagsUseCase = Depends(get_list_tags_use_case),
) -> TagsResponse:
    """Return all tags for a table."""
    result = use_case.execute(ListTagsInput(namespace=namespace, table=table))
    return TagsResponse(
        tags=[
            TagResponse(
                name=t.name,
                snapshot_id=t.snapshot_id,
                max_ref_age_ms=t.max_ref_age_ms,
            )
            for t in result.tags
        ],
    )
