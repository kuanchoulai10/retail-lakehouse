"""Define the GetTableCurrentMetricsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS, TableStatus
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableCurrentMetricsUseCase,
    GetTableCurrentMetricsUseCaseInput,
    GetTableCurrentMetricsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TableMetricsStore, TablesRepo


class GetTableCurrentMetricsService(GetTableCurrentMetricsUseCase):
    """Get the saved metrics of a managed table."""

    def __init__(self, tables_repo: TablesRepo, metrics_store: TableMetricsStore) -> None:
        """Bind the tables repo, which says whether the table is managed, and the metrics store."""
        self._tables_repo = tables_repo
        self._metrics_store = metrics_store

    def execute(self, request: GetTableCurrentMetricsUseCaseInput) -> GetTableCurrentMetricsUseCaseOutput:
        """Return the table's metrics; both fields are None when it is not managed or has no row."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        metrics = self._metrics_store.get(table.id) if table.status is TableStatus.MANAGED else None
        if metrics is None:
            return GetTableCurrentMetricsUseCaseOutput(observed_at=None, counts=None)
        return GetTableCurrentMetricsUseCaseOutput(
            observed_at=metrics.observed_at,
            counts={field: getattr(metrics, field) for field in TABLE_METRIC_COUNT_FIELDS},
        )
