"""Define the NamespacesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.namespace.sql.namespace_row_mapper import NamespaceRowMapper
from context.table_maintenance.adapter.outbound.namespace.sql.namespaces_table import namespaces_table as t
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine, Select

    from base import EntityId
    from context.table_maintenance.application.port.outbound.namespace import Namespace

_ORDER = (t.c.catalog, t.c.id)


class NamespacesSqlRepo(NamespacesRepo):
    """Store Namespace records in a SQL database, one row per namespace id."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: Namespace) -> Namespace:
        """Insert the namespace; a stored id, or a policy that does not exist, raises ConflictError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**NamespaceRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> Namespace | None:
        """Return the namespace with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else NamespaceRowMapper.to_aggregate(row._mapping)

    def get_many(self, ids: Sequence[EntityId]) -> list[Namespace]:
        """Return the namespaces that exist among the ids, by catalog and levels."""
        if not ids:
            return []
        return self._read(select(t).where(t.c.id.in_([i.value for i in ids])))

    def list_all(self) -> list[Namespace]:
        """Return every namespace, by catalog and levels."""
        return self._read(select(t))

    def list_in_catalog(self, catalog: str) -> list[Namespace]:
        """Return the namespaces of ``catalog``, by levels, a parent before the namespaces under it."""
        return self._read(select(t).where(t.c.catalog == catalog))

    def update(self, namespace: Namespace) -> Namespace:
        """Persist the changed namespace when the row is still at its version, and return the row read back.

        The write matches the id and the version the namespace was read at, and moves the version on
        by one, so a copy read before another save is refused (``ConcurrentUpdateError``). An id with no
        row raises ``LookupError``, and a policy that does not exist raises ``ConflictError``.
        """
        values = NamespaceRowMapper.to_values(namespace)
        values["version"] = namespace.version + 1
        stmt = (
            update(t)
            .where(t.c.id == namespace.id.value, t.c.version == namespace.version)
            .values(**values)
            .returning(*t.c)
        )
        described = f"namespace {'.'.join(namespace.levels)} of {namespace.catalog}"
        try:
            with self._engine.begin() as conn:
                row = conn.execute(stmt).first()
                if row is None:
                    if conn.execute(select(t.c.id).where(t.c.id == namespace.id.value)).first() is None:
                        raise LookupError(f"{described} does not exist")
                    raise ConcurrentUpdateError(f"{described} was changed by someone else")
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return NamespaceRowMapper.to_aggregate(row._mapping)

    def _read(self, stmt: Select) -> list[Namespace]:
        """Run ``stmt`` ordered by catalog and id; the id joins the levels with U+001F, so a parent sorts first."""
        with self._engine.connect() as conn:
            rows = conn.execute(stmt.order_by(*_ORDER)).all()
        return [NamespaceRowMapper.to_aggregate(r._mapping) for r in rows]
