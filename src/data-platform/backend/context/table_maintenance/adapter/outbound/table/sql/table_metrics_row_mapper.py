"""Define the TableMetricsRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table import (
    TABLE_METRIC_COUNT_FIELDS,
    TableId,
    TableMetrics,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableMetricsRowMapper:
    """Map a table's metrics to its row and back."""

    @staticmethod
    def to_values(metrics: TableMetrics) -> dict[str, Any]:
        """Return the column values of the metrics' row."""
        return {
            "table_uuid": metrics.table_id.value,
            "observed_at": metrics.observed_at,
            **{name: getattr(metrics, name) for name in TABLE_METRIC_COUNT_FIELDS},
        }

    @staticmethod
    def to_value_object(row: RowMapping) -> TableMetrics:
        """Rebuild the metrics from their row."""
        counts = {name: row[name] for name in TABLE_METRIC_COUNT_FIELDS}
        return TableMetrics(table_id=TableId(row["table_uuid"]), observed_at=row["observed_at"], **counts)
