"""Define the TableMetricsSqlStore."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table.sql.table_metrics_row_mapper import TableMetricsRowMapper
from context.table_maintenance.adapter.outbound.table.sql.table_metrics_table import table_metrics_table as t
from context.table_maintenance.application.port.outbound.table import TableMetricsStore

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table import TableId, TableMetrics


class TableMetricsSqlStore(TableMetricsStore):
    """Store each table's newest metrics in a SQL database, one row per table."""

    def __init__(self, engine: Engine) -> None:
        """Bind the store to an engine."""
        self._engine = engine

    def save(self, metrics: TableMetrics) -> None:
        """Insert the table's row, or replace it when these metrics were observed later.

        A plan retried after a newer one landed saves an older observation, which changes
        nothing. When two first saves of a table both find no row and insert, the one that
        loses the race on the primary key tries again and takes the update path.
        """
        try:
            self._save_once(metrics)
        except IntegrityError:
            self._save_once(metrics)

    def _save_once(self, metrics: TableMetrics) -> None:
        values = TableMetricsRowMapper.to_values(metrics)
        forward = update(t).where(t.c.table_uuid == values["table_uuid"], t.c.observed_at < metrics.observed_at)
        with self._engine.begin() as conn:
            if conn.execute(forward.values(**values)).rowcount:
                return
            if conn.execute(select(t.c.table_uuid).where(t.c.table_uuid == values["table_uuid"])).first() is not None:
                return
            conn.execute(insert(t).values(**values))

    def get(self, table_id: TableId) -> TableMetrics | None:
        """Return the table's newest metrics, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.table_uuid == table_id.value)).first()
        return None if row is None else TableMetricsRowMapper.to_value_object(row._mapping)

    def list_all(self) -> list[TableMetrics]:
        """Return every table's metrics, by table uuid."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.table_uuid)).all()
        return [TableMetricsRowMapper.to_value_object(r._mapping) for r in rows]

    def delete(self, table_id: TableId) -> None:
        """Remove the table's metrics; nothing happens when there are none."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.table_uuid == table_id.value))
