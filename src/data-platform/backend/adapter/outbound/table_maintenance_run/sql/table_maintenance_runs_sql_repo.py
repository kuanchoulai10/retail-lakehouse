"""Define the TableMaintenanceRunsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.table_maintenance_run.sql.table_maintenance_run_row_mapper import (
    TableMaintenanceRunRowMapper,
)
from adapter.outbound.table_maintenance_run.sql.table_maintenance_runs_table import (
    table_maintenance_runs_table as t,
)
from application.exceptions import ConflictError
from application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import Engine

    from application.port.outbound.table_maintenance_run import (
        TableId,
        TableMaintenanceRun,
    )
    from base import EntityId


class TableMaintenanceRunsSqlRepo(TableMaintenanceRunsRepo):
    """Store TableMaintenanceRun aggregates in a SQL database.

    The operations of a run are stored as JSON on the run row.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableMaintenanceRun) -> TableMaintenanceRun:
        """Insert a new run."""
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    insert(t).values(**TableMaintenanceRunRowMapper.to_values(entity))
                )
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenanceRun | None:
        """Return the run with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return (
            None
            if row is None
            else TableMaintenanceRunRowMapper.to_aggregate(row._mapping)
        )

    def list_all(self) -> list[TableMaintenanceRun]:
        """Return all runs, newest first."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(t).order_by(t.c.created_at.desc(), t.c.id.desc())
            ).all()
        return [TableMaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, run: TableMaintenanceRun) -> TableMaintenanceRun:
        """Persist the changed run."""
        values = TableMaintenanceRunRowMapper.to_values(run)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.id == run.id.value).values(**values)
            )
            if result.rowcount == 0:
                raise LookupError(f"maintenance run {run.id.value} does not exist")
        return run

    def list_by_table(
        self, table_uuid: TableId, limit: int = 50
    ) -> list[TableMaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first."""
        stmt = (
            select(t)
            .where(t.c.table_uuid == table_uuid.value)
            .order_by(t.c.created_at.desc(), t.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [TableMaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_by_table_since(
        self, table_uuid: TableId, since: datetime
    ) -> list[TableMaintenanceRun]:
        """Return the table's runs created at or after since, newest first."""
        stmt = (
            select(t)
            .where(t.c.table_uuid == table_uuid.value, t.c.created_at >= since)
            .order_by(t.c.created_at.desc(), t.c.id.desc())
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [TableMaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]
