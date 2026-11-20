"""Define the TableMetricsStore outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Store

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableId, TableMetrics


class TableMetricsStore(Store):
    """Keep the newest metrics of each table, one row per table."""

    @abstractmethod
    def save(self, metrics: TableMetrics) -> None:
        """Insert the table's metrics, or replace the stored ones only when these were observed later."""

    @abstractmethod
    def get(self, table_id: TableId) -> TableMetrics | None:
        """Return the table's newest metrics, or None."""

    @abstractmethod
    def list_all(self) -> list[TableMetrics]:
        """Return every table's metrics, by table uuid."""

    @abstractmethod
    def delete(self, table_id: TableId) -> None:
        """Remove the table's metrics; nothing happens when there are none."""
