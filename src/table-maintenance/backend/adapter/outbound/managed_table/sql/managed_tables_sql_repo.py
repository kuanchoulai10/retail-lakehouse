"""Define the ManagedTablesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.managed_table.sql.managed_table_row_mapper import (
    ManagedTableRowMapper,
)
from adapter.outbound.managed_table.sql.managed_tables_table import (
    managed_tables_table as t,
)
from application.domain.model.managed_table.table_status import TableStatus
from application.exceptions import ConflictError
from application.port.outbound.managed_table.managed_tables_repo import (
    ManagedTablesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine

    from application.domain.model.managed_table.managed_table import ManagedTable
    from application.domain.model.managed_table.table_name import TableName
    from base.entity_id import EntityId

_ORDER = (t.c.catalog, t.c.namespace, t.c.table_name)


class ManagedTablesSqlRepo(ManagedTablesRepo):
    """Store ManagedTable aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: ManagedTable) -> ManagedTable:
        """Insert a new table."""
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    insert(t).values(**ManagedTableRowMapper.to_values(entity))
                )
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> ManagedTable | None:
        """Return the table with the given uuid, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.uuid == entity_id.value)).first()
        return None if row is None else ManagedTableRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[ManagedTable]:
        """Return all tables ordered by (catalog, namespace, table_name)."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(*_ORDER, t.c.uuid)).all()
        return [ManagedTableRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, table: ManagedTable) -> ManagedTable:
        """Persist the changed table."""
        values = ManagedTableRowMapper.to_values(table)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.uuid == table.id.value).values(**values)
            )
            if result.rowcount == 0:
                raise LookupError(f"managed table {table.id.value} does not exist")
        return table

    def find_by_name(self, name: TableName) -> ManagedTable | None:
        """Return the latest-updated non-dropped table with this name."""
        stmt = (
            select(t)
            .where(
                t.c.catalog == name.catalog,
                t.c.namespace == name.namespace,
                t.c.table_name == name.table,
                t.c.status != TableStatus.DROPPED.value,
            )
            .order_by(t.c.updated_at.desc(), t.c.uuid)
            .limit(1)
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        return None if row is None else ManagedTableRowMapper.to_aggregate(row._mapping)

    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[ManagedTable]:
        """Return the tables with one of the statuses."""
        if not statuses:
            return []
        stmt = (
            select(t)
            .where(t.c.status.in_([s.value for s in statuses]))
            .order_by(*_ORDER, t.c.uuid)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [ManagedTableRowMapper.to_aggregate(r._mapping) for r in rows]
