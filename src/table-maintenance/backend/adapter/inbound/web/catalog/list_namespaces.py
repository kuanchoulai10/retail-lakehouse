"""Define the GET /catalogs/{catalog}/namespaces endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import NamespacesResponse
from application.port.inbound.catalog.list_namespaces import (
    ListNamespacesInput,
    ListNamespacesUseCase,
)
from dependencies.use_cases import get_list_namespaces_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces",
    response_model=NamespacesResponse,
)
def list_namespaces(
    catalog: str,
    use_case: ListNamespacesUseCase = Depends(get_list_namespaces_use_case),
) -> NamespacesResponse:
    """Return all namespaces in the catalog."""
    result = use_case.execute(ListNamespacesInput())
    return NamespacesResponse(namespaces=result.namespaces)
