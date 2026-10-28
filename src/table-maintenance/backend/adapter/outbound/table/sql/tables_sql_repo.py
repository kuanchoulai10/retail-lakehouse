"""Define the TablesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.table.sql.table_row_mapper import (
    TableRowMapper,
)
from adapter.outbound.table.sql.tables_table import (
    tables_table as t,
)
from application.exceptions import ConflictError
from application.port.outbound.table import TablesRepo, TableStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine

    from application.port.outbound.table import Table, TableName
    from base import EntityId

_ORDER = (t.c.catalog, t.c.namespace, t.c.table_name)


class TablesSqlRepo(TablesRepo):
    """Store Table aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: Table) -> Table:
        """Insert a new table."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**TableRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> Table | None:
        """Return the table with the given uuid, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.uuid == entity_id.value)).first()
        return None if row is None else TableRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[Table]:
        """Return all tables ordered by (catalog, namespace, table_name)."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(*_ORDER, t.c.uuid)).all()
        return [TableRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, table: Table) -> Table:
        """Persist the changed table."""
        values = TableRowMapper.to_values(table)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.uuid == table.id.value).values(**values)
            )
            if result.rowcount == 0:
                raise LookupError(f"table {table.id.value} does not exist")
        return table

    def find_by_name(self, name: TableName) -> Table | None:
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
        return None if row is None else TableRowMapper.to_aggregate(row._mapping)

    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[Table]:
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
        return [TableRowMapper.to_aggregate(r._mapping) for r in rows]
