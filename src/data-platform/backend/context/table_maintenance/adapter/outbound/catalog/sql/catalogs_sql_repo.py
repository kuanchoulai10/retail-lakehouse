"""Define the CatalogsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.catalog.sql.catalog_row_mapper import CatalogRowMapper
from context.table_maintenance.adapter.outbound.catalog.sql.catalogs_table import catalogs_table as t
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.catalog import Catalog


class CatalogsSqlRepo(CatalogsRepo):
    """Store Catalog records in a SQL database, one row per catalog name."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: Catalog) -> Catalog:
        """Insert the catalog; a stored name, or a policy that does not exist, raises ConflictError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**CatalogRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> Catalog | None:
        """Return the catalog with the given name, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.name == entity_id.value)).first()
        return None if row is None else CatalogRowMapper.to_aggregate(row._mapping)

    def get_many(self, ids: Sequence[EntityId]) -> list[Catalog]:
        """Return the catalogs that exist among the ids, by name."""
        if not ids:
            return []
        stmt = select(t).where(t.c.name.in_([i.value for i in ids])).order_by(t.c.name)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [CatalogRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_all(self) -> list[Catalog]:
        """Return every catalog, by name."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.name)).all()
        return [CatalogRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, catalog: Catalog) -> Catalog:
        """Persist the changed catalog when the row is still at its version, and return the row read back.

        The write matches the name and the version the catalog was read at, and moves the version on
        by one, so a copy read before another save is refused (``ConcurrentUpdateError``) instead of
        putting that save back. A name with no row raises ``LookupError``, and a policy that does not
        exist (deleted since it was read) raises ``ConflictError``.
        """
        values = CatalogRowMapper.to_values(catalog)
        values["version"] = catalog.version + 1
        stmt = (
            update(t)
            .where(t.c.name == catalog.id.value, t.c.version == catalog.version)
            .values(**values)
            .returning(*t.c)
        )
        try:
            with self._engine.begin() as conn:
                row = conn.execute(stmt).first()
                if row is None:
                    if conn.execute(select(t.c.name).where(t.c.name == catalog.id.value)).first() is None:
                        raise LookupError(f"catalog {catalog.id.value} does not exist")
                    raise ConcurrentUpdateError(f"catalog {catalog.id.value} was changed by someone else")
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return CatalogRowMapper.to_aggregate(row._mapping)
