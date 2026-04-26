"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.adapter.inbound.web.catalog.dto import TablesResponse
from core.application.port.inbound.catalog.list_tables import (
    ListTablesInput,
    ListTablesUseCase,
)
from dependencies.use_cases import get_list_tables_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables",
    response_model=TablesResponse,
)
def list_tables(
    catalog: str,
    namespace: str,
    use_case: ListTablesUseCase = Depends(get_list_tables_use_case),
) -> TablesResponse:
    """Return all tables in the namespace."""
    result = use_case.execute(ListTablesInput(namespace=namespace))
    return TablesResponse(tables=result.tables)
