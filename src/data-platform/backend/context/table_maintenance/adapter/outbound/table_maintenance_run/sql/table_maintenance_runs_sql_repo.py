"""Define the TableMaintenanceRunsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import case, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_maintenance_run.sql.table_maintenance_run_row_mapper import (
    TableMaintenanceRunRowMapper,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.sql.table_maintenance_runs_table import (
    table_maintenance_runs_table as t,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    MaintenanceOperation,
    TableMaintenanceRunsRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableId,
        TableMaintenanceRun,
    )

_PLAN_POSITION = case(
    {op.value: position for position, op in enumerate(MaintenanceOperation.ordered())},
    value=t.c.operation,
)
_NEWEST_FIRST = (t.c.created_at.desc(), _PLAN_POSITION.desc(), t.c.id.desc())


class TableMaintenanceRunsSqlRepo(TableMaintenanceRunsRepo):
    """Store TableMaintenanceRun aggregates in a SQL database.

    The columns a run is read or sorted by are real columns; its job content, metrics and attempts are
    stored as JSON on the run row.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableMaintenanceRun) -> TableMaintenanceRun:
        """Insert a new run."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**TableMaintenanceRunRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def create_all(self, runs: Sequence[TableMaintenanceRun]) -> list[TableMaintenanceRun]:
        """Insert new runs in one transaction; a run that cannot be stored rolls back every one."""
        stored = list(runs)
        if not stored:
            return stored
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t), [TableMaintenanceRunRowMapper.to_values(run) for run in stored])
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return stored

    def get(self, entity_id: EntityId) -> TableMaintenanceRun | None:
        """Return the run with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else TableMaintenanceRunRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[TableMaintenanceRun]:
        """Return all runs, newest first, in the order ``list_by_table`` lists a table's runs."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(*_NEWEST_FIRST)).all()
        return [TableMaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, run: TableMaintenanceRun) -> TableMaintenanceRun:
        """Persist the changed run."""
        values = TableMaintenanceRunRowMapper.to_values(run)
        with self._engine.begin() as conn:
            result = conn.execute(update(t).where(t.c.id == run.id.value).values(**values))
            if result.rowcount == 0:
                raise LookupError(f"maintenance run {run.id.value} does not exist")
        return run

    def list_by_table(self, table_uuid: TableId, limit: int = 50) -> list[TableMaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first.

        The runs one plan created share a creation time; among them the plan's last operation lists first,
        and runs of one time and one operation list by id, the larger first.
        """
        stmt = select(t).where(t.c.table_uuid == table_uuid.value).order_by(*_NEWEST_FIRST).limit(limit)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [TableMaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]
