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
    TableCurrentMetricsApiResponse,
    TableMetricTrendsApiResponse,
    TableMetricValuesApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    TriggerTableReconciliationApiResponse,
)
from context.table_maintenance.application.port.inbound.table import (
    GetTableCurrentMetricsUseCaseInput,
    GetTableMetricTrendsUseCaseInput,
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


@router.get("/{table_uuid}/metrics/current")
def get_table_current_metrics(table_uuid: str, use_cases: UseCases) -> TableCurrentMetricsApiResponse:
    """Return a table's newest metrics; both fields are null when it is not managed or not reconciled yet."""
    output = use_cases.get_table_current_metrics.execute(GetTableCurrentMetricsUseCaseInput(uuid=table_uuid))
    return TableCurrentMetricsApiResponse(
        observed_at=output.observed_at,
        metrics=None if output.counts is None else TableMetricValuesApiResponse(**output.counts),
    )


@router.get("/{table_uuid}/metrics")
def get_table_metric_trends(
    table_uuid: str,
    use_cases: UseCases,
    time_range: Annotated[Literal["1h", "3h", "6h"], Query(alias="range")] = "6h",
) -> TableMetricTrendsApiResponse:
    """Return how a table's metrics changed over the last 1, 3 or 6 hours; 502 when the history is unavailable."""
    output = use_cases.get_table_metric_trends.execute(
        GetTableMetricTrendsUseCaseInput(uuid=table_uuid, time_range=time_range, now=datetime.now(UTC))
    )
    return TableMetricTrendsApiResponse.model_validate(output)


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
    use_cases.set_table_priority.execute(SetTablePriorityUseCaseInput(uuid=table_uuid, priority=body.priority))
    output = use_cases.get_table.execute(GetTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.post("/{table_uuid}/maintenance", status_code=status.HTTP_202_ACCEPTED)
def trigger_table_maintenance(
    table_uuid: str, body: TriggerTableMaintenanceApiRequest, use_cases: UseCases
) -> TriggerTableMaintenanceApiResponse:
    """Run the given operations on a table now."""
    output = use_cases.trigger_table_maintenance.execute(
        TriggerTableMaintenanceUseCaseInput(uuid=table_uuid, operations=tuple(body.operations), priority=body.priority)
    )
    return TriggerTableMaintenanceApiResponse.model_validate(output)


@router.post("/{table_uuid}/reconcile", status_code=status.HTTP_202_ACCEPTED)
def trigger_table_reconciliation(table_uuid: str, use_cases: UseCases) -> TriggerTableReconciliationApiResponse:
    """Reconcile a table now by the normal rules, after any run in flight."""
    output = use_cases.trigger_table_reconciliation.execute(TriggerTableReconciliationUseCaseInput(uuid=table_uuid))
    return TriggerTableReconciliationApiResponse.model_validate(output)
