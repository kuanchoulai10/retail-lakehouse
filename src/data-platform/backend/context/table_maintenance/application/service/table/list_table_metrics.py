"""Define the ListTableMetricsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS, TableStatus
from context.table_maintenance.application.port.inbound.table import (
    ListTableMetricsUseCase,
    ListTableMetricsUseCaseInput,
    ListTableMetricsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TableMetricsStore, TablesRepo


class ListTableMetricsService(ListTableMetricsUseCase):
    """List the saved metrics of the managed tables, named as the tables are named now."""

    def __init__(self, tables_repo: TablesRepo, metrics_store: TableMetricsStore) -> None:
        """Bind the tables repo, which says which tables are managed, and the metrics store."""
        self._tables_repo = tables_repo
        self._metrics_store = metrics_store

    def execute(self, request: ListTableMetricsUseCaseInput) -> ListTableMetricsUseCaseOutput:
        """Return the metrics of every managed table by uuid; a row of any other table is left out."""
        managed = {t.id.value: t.name for t in self._tables_repo.list_by_statuses([TableStatus.MANAGED])}
        return ListTableMetricsUseCaseOutput(
            tables=tuple(
                ListTableMetricsUseCaseOutput.Table(
                    table_uuid=metrics.table_id.value,
                    catalog=managed[metrics.table_id.value].catalog,
                    namespace=managed[metrics.table_id.value].namespace,
                    table=managed[metrics.table_id.value].table,
                    observed_at=metrics.observed_at,
                    counts={field: getattr(metrics, field) for field in TABLE_METRIC_COUNT_FIELDS},
                )
                for metrics in self._metrics_store.list_all()
                if metrics.table_id.value in managed
            )
        )
