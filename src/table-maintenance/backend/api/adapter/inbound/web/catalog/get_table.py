"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.adapter.inbound.web.catalog.dto import (
    SchemaFieldResponse,
    SchemaResponse,
    TableDetailResponse,
)
from core.application.port.inbound.catalog.get_table import (
    GetTableInput,
    GetTableUseCase,
)
from dependencies.use_cases import get_get_table_use_case

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}",
    response_model=TableDetailResponse,
)
def get_table(
    catalog: str,
    namespace: str,
    table: str,
    use_case: GetTableUseCase = Depends(get_get_table_use_case),
) -> TableDetailResponse:
    """Return metadata for a specific table."""
    result = use_case.execute(GetTableInput(namespace=namespace, table=table))
    return TableDetailResponse(
        table=result.name,
        namespace=result.namespace,
        location=result.location,
        current_snapshot_id=result.current_snapshot_id,
        schema=SchemaResponse(
            fields=[
                SchemaFieldResponse(
                    id=f.field_id,
                    name=f.name,
                    type=f.field_type,
                    required=f.required,
                )
                for f in result.schema.fields
            ],
        ),
        properties=result.properties,
    )
