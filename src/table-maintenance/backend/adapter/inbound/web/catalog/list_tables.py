"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TablesApiResponse
from application.port.inbound.catalog.list_tables import (
    ListTablesUseCaseInput,
    ListTablesUseCase,
)
from bootstrap.dependencies.use_cases import get_list_tables_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables",
    response_model=TablesApiResponse,
)
def list_tables(
    catalog: str,
    namespace: str,
    use_case: ListTablesUseCase = Depends(get_list_tables_use_case),
) -> TablesApiResponse:
    """Return all tables in the namespace."""
    result = use_case.execute(ListTablesUseCaseInput(namespace=namespace))
    return TablesApiResponse(tables=result.tables)
