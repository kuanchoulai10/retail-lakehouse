"""Define the table reconciliation router."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - FastAPI resolves the annotation at runtime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_reconciliation.dto import (
    TableReconciliationApiResponse,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    GetTableReconciliationUseCaseInput,
    ListTableReconciliationsUseCaseInput,
)

router = APIRouter(tags=["table-reconciliations"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]
ReconciliationId = Annotated[
    str,
    Path(description="An `rc-` id (prefix, dash, 26 lowercase Crockford base32 characters; ADR 0011)."),
]


@router.get("/tables/{table_uuid}/reconciliations")
def list_table_reconciliations(
    table_uuid: str,
    use_cases: UseCases,
    before: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[TableReconciliationApiResponse]:
    """List a table's reconciliations, newest first, strictly before ``before``."""
    output = use_cases.list_table_reconciliations.execute(
        ListTableReconciliationsUseCaseInput(table_uuid=table_uuid, before=before, limit=limit)
    )
    return [TableReconciliationApiResponse.model_validate(item) for item in output.items]


@router.get("/table-reconciliations/{reconciliation_id}")
def get_table_reconciliation(
    reconciliation_id: ReconciliationId, use_cases: UseCases
) -> TableReconciliationApiResponse:
    """Return one reconciliation by its id, wherever it sits in the table's history."""
    output = use_cases.get_table_reconciliation.execute(
        GetTableReconciliationUseCaseInput(reconciliation_id=reconciliation_id)
    )
    return TableReconciliationApiResponse.model_validate(output)
