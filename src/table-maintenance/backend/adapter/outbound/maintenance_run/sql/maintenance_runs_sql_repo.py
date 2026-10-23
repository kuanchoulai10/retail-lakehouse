"""Define the MaintenanceRunsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.maintenance_run.sql.maintenance_run_row_mapper import (
    MaintenanceRunRowMapper,
)
from adapter.outbound.maintenance_run.sql.maintenance_runs_table import (
    maintenance_runs_table as t,
)
from application.exceptions import ConflictError
from application.port.outbound.maintenance_run.maintenance_runs_repo import (
    MaintenanceRunsRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from application.domain.model.maintenance_run.maintenance_run import (
        MaintenanceRun,
    )
    from application.domain.model.managed_table.table_uuid import TableUuid
    from base.entity_id import EntityId


class MaintenanceRunsSqlRepo(MaintenanceRunsRepo):
    """Store MaintenanceRun aggregates in a SQL database.

    The operations of a run are stored as JSON on the run row.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: MaintenanceRun) -> MaintenanceRun:
        """Insert a new run."""
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    insert(t).values(**MaintenanceRunRowMapper.to_values(entity))
                )
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> MaintenanceRun | None:
        """Return the run with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return (
            None if row is None else MaintenanceRunRowMapper.to_aggregate(row._mapping)
        )

    def list_all(self) -> list[MaintenanceRun]:
        """Return all runs, newest first."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(t).order_by(t.c.created_at.desc(), t.c.id.desc())
            ).all()
        return [MaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, run: MaintenanceRun) -> MaintenanceRun:
        """Persist the changed run."""
        values = MaintenanceRunRowMapper.to_values(run)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.id == run.id.value).values(**values)
            )
            if result.rowcount == 0:
                raise LookupError(f"maintenance run {run.id.value} does not exist")
        return run

    def list_by_table(
        self, table_uuid: TableUuid, limit: int = 50
    ) -> list[MaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first."""
        stmt = (
            select(t)
            .where(t.c.table_uuid == table_uuid.value)
            .order_by(t.c.created_at.desc(), t.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [MaintenanceRunRowMapper.to_aggregate(r._mapping) for r in rows]
