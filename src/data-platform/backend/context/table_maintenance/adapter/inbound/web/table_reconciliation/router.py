"""Define the table reconciliation router."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - FastAPI resolves the annotation at runtime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_reconciliation.dto import (
    TableReconciliationApiResponse,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCaseInput,
)

router = APIRouter(tags=["table-reconciliations"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


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
