"""Define the TablesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import case, insert, literal, or_, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime
from context.table_maintenance.adapter.outbound.table.sql.table_row_mapper import (
    TableRowMapper,
    encode_over_target_partitions,
)
from context.table_maintenance.adapter.outbound.table.sql.tables_table import (
    tables_table as t,
)
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from context.table_maintenance.application.port.outbound.table import (
    TablesRepo,
    TableStatus,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from sqlalchemy import ColumnElement, Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table import (
        OverTargetPartition,
        Table,
        TableId,
        TableName,
    )

_ORDER = (t.c.catalog, t.c.namespace, t.c.table_name)


class TablesSqlRepo(TablesRepo):
    """Store Table aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: Table) -> Table:
        """Insert a new table, always with an empty over-target record, whatever the entity holds."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**TableRowMapper.to_values(entity), over_target_partitions_json=[]))
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
        """Persist the changed table when the row is still at its version, and return the row read back.

        The write matches the uuid and the version the table was read at, and moves the version
        on by one, so a copy read before another save is refused (``ConcurrentUpdateError``)
        instead of putting that save back. A uuid with no row raises ``LookupError``, and a policy
        the table holds that does not exist raises ``ConflictError``. The stored last commit is
        kept when the table's is older or unknown.
        """
        values = TableRowMapper.to_values(table)
        values["version"] = table.version + 1
        committed = values.pop("last_committed_at")
        if committed is not None:
            values["last_committed_at"] = case(
                (_commit_moves(committed), literal(committed, UtcDateTime())),
                else_=t.c.last_committed_at,
            )
        stmt = (
            update(t).where(t.c.uuid == table.id.value, t.c.version == table.version).values(**values).returning(*t.c)
        )
        try:
            with self._engine.begin() as conn:
                row = conn.execute(stmt).first()
                if row is None:
                    if conn.execute(select(t.c.uuid).where(t.c.uuid == table.id.value)).first() is None:
                        raise LookupError(f"table {table.id.value} does not exist")
                    raise ConcurrentUpdateError(f"table {table.id.value} was changed by someone else")
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return TableRowMapper.to_aggregate(row._mapping)

    def record_last_commit(self, table_id: TableId, at: datetime) -> bool:
        """Write only the last commit, when ``at`` is newer and the table is not dropped."""
        stmt = (
            update(t)
            .where(t.c.uuid == table_id.value, t.c.status != TableStatus.DROPPED.value, _commit_moves(at))
            .values(last_committed_at=at)
        )
        with self._engine.begin() as conn:
            return conn.execute(stmt).rowcount == 1

    def record_over_target_partitions(self, table_id: TableId, partitions: Sequence[OverTargetPartition]) -> bool:
        """Write only the over-target partitions, when the table exists and is not dropped."""
        stmt = (
            update(t)
            .where(t.c.uuid == table_id.value, t.c.status != TableStatus.DROPPED.value)
            .values(over_target_partitions_json=encode_over_target_partitions(partitions))
        )
        with self._engine.begin() as conn:
            return conn.execute(stmt).rowcount == 1

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
        stmt = select(t).where(t.c.status.in_([s.value for s in statuses])).order_by(*_ORDER, t.c.uuid)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [TableRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_catalogs_with_managed_tables(self) -> list[str]:
        """Return each catalog that holds a managed table, once and sorted."""
        stmt = select(t.c.catalog).where(t.c.status == TableStatus.MANAGED.value).distinct().order_by(t.c.catalog)
        with self._engine.connect() as conn:
            return list(conn.execute(stmt).scalars())


def _commit_moves(at: datetime) -> ColumnElement[bool]:
    """Say, in SQL, whether ``at`` is newer than the stored last commit (CASE-friendly on SQLite and Postgres)."""
    return or_(t.c.last_committed_at.is_(None), t.c.last_committed_at < at)
