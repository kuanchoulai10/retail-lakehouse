"""Define the InMemoryTableMetricsStore test fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import TableMetricsStore

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TableId, TableMetrics


class InMemoryTableMetricsStore(TableMetricsStore):
    """Keep metrics in a dict keyed by table uuid.

    A save moves a stored observation only forward, as the SQL store does.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableMetrics] = {}

    def save(self, metrics: TableMetrics) -> None:
        """Insert the metrics, or replace the stored ones when these were observed later."""
        stored = self.items.get(metrics.table_id.value)
        if stored is None or stored.observed_at < metrics.observed_at:
            self.items[metrics.table_id.value] = metrics

    def get(self, table_id: TableId) -> TableMetrics | None:
        """Return the table's metrics, or None."""
        return self.items.get(table_id.value)

    def list_all(self) -> list[TableMetrics]:
        """Return every table's metrics, by table uuid."""
        return [self.items[k] for k in sorted(self.items)]

    def delete(self, table_id: TableId) -> None:
        """Remove the table's metrics; nothing happens when there are none."""
        self.items.pop(table_id.value, None)
