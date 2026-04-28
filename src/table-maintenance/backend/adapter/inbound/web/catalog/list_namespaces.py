"""Define the GET /catalogs/{catalog}/namespaces endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import NamespacesApiResponse
from application.port.inbound.catalog.list_namespaces import (
    ListNamespacesUseCaseInput,
    ListNamespacesUseCase,
)
from bootstrap.dependencies.use_cases import get_list_namespaces_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces",
    response_model=NamespacesApiResponse,
)
def list_namespaces(
    catalog: str,
    use_case: ListNamespacesUseCase = Depends(get_list_namespaces_use_case),
) -> NamespacesApiResponse:
    """Return all namespaces in the catalog."""
    result = use_case.execute(ListNamespacesUseCaseInput())
    return NamespacesApiResponse(namespaces=result.namespaces)
