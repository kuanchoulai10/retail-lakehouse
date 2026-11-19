"""Define the table router."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table.dto import (
    SetTablePriorityApiRequest,
    TableApiResponse,
    TableCommitsApiResponse,
    TableHealthApiResponse,
    TableStorageApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    TriggerTableReconciliationApiResponse,
)
from context.table_maintenance.application.port.inbound.table import (
    GetTableHealthUseCaseInput,
    GetTableStorageUseCaseInput,
    GetTableUseCaseInput,
    ListTableCommitsUseCaseInput,
    ListTablesUseCaseInput,
    SetTablePriorityUseCaseInput,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableReconciliationUseCaseInput,
)

router = APIRouter(prefix="/tables", tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("")
def list_tables(use_cases: UseCases, status: str | None = None) -> list[TableApiResponse]:
    """List the tables, optionally only those in one status."""
    output = use_cases.list_tables.execute(ListTablesUseCaseInput(status=status))
    return [TableApiResponse.model_validate(item) for item in output.items]


@router.get("/{table_uuid}")
def get_table(table_uuid: str, use_cases: UseCases) -> TableApiResponse:
    """Return one table."""
    output = use_cases.get_table.execute(GetTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.get("/{table_uuid}/health")
def get_table_health(table_uuid: str, use_cases: UseCases) -> TableHealthApiResponse:
    """Return the scheduler's maintenance evaluation of one table."""
    output = use_cases.get_table_health.execute(GetTableHealthUseCaseInput(uuid=table_uuid))
    return TableHealthApiResponse.model_validate(output)


@router.get("/{table_uuid}/storage")
def get_table_storage(table_uuid: str, use_cases: UseCases) -> TableStorageApiResponse:
    """Return the current and old-snapshot storage of one table."""
    output = use_cases.get_table_storage.execute(GetTableStorageUseCaseInput(uuid=table_uuid))
    return TableStorageApiResponse.model_validate(output)


@router.get("/{table_uuid}/commits")
def list_table_commits(
    table_uuid: str,
    use_cases: UseCases,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    since: datetime | None = None,
    before: datetime | None = None,
    writer: Literal["kafka_connect", "spark", "unknown"] | None = None,
) -> TableCommitsApiResponse:
    """Return the commits of one table, newest first: at or after ``since``, before ``before``, by ``writer``."""
    output = use_cases.list_table_commits.execute(
        ListTableCommitsUseCaseInput(uuid=table_uuid, limit=limit, since=since, before=before, writer=writer)
    )
    return TableCommitsApiResponse.model_validate(output)


@router.put("/{table_uuid}/priority")
def set_table_priority(table_uuid: str, body: SetTablePriorityApiRequest, use_cases: UseCases) -> TableApiResponse:
    """Set how urgently a table's maintenance is scheduled; answers the updated table."""
    use_cases.set_table_priority.execute(
        SetTablePriorityUseCaseInput(uuid=table_uuid, priority=body.priority, now=datetime.now(UTC))
    )
    output = use_cases.get_table.execute(GetTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.post("/{table_uuid}/maintenance", status_code=status.HTTP_202_ACCEPTED)
def trigger_table_maintenance(
    table_uuid: str, body: TriggerTableMaintenanceApiRequest, use_cases: UseCases
) -> TriggerTableMaintenanceApiResponse:
    """Run the given operations on a table now."""
    output = use_cases.trigger_table_maintenance.execute(
        TriggerTableMaintenanceUseCaseInput(uuid=table_uuid, operations=tuple(body.operations))
    )
    return TriggerTableMaintenanceApiResponse.model_validate(output)


@router.post("/{table_uuid}/reconcile", status_code=status.HTTP_202_ACCEPTED)
def trigger_table_reconciliation(table_uuid: str, use_cases: UseCases) -> TriggerTableReconciliationApiResponse:
    """Reconcile a table now by the normal rules, after any run in flight."""
    output = use_cases.trigger_table_reconciliation.execute(TriggerTableReconciliationUseCaseInput(uuid=table_uuid))
    return TriggerTableReconciliationApiResponse.model_validate(output)
