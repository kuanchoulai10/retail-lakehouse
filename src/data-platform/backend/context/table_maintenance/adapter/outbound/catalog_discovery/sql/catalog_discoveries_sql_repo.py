"""Define the CatalogDiscoveriesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.catalog_discovery.sql.catalog_discoveries_table import (
    catalog_discoveries_table as t,
)
from context.table_maintenance.adapter.outbound.catalog_discovery.sql.catalog_discovery_row_mapper import (
    CatalogDiscoveryRowMapper,
)
from context.table_maintenance.application.port.outbound.catalog_discovery import CatalogDiscoveriesRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.catalog_discovery import CatalogDiscovery


class CatalogDiscoveriesSqlRepo(CatalogDiscoveriesRepo):
    """Store CatalogDiscovery records in a SQL database, one row per catalog."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: CatalogDiscovery) -> CatalogDiscovery:
        """Insert or replace the record."""
        self.save(entity)
        return entity

    def save(self, entity: CatalogDiscovery) -> None:
        """Insert the catalog's row, or move its time forward; an older time never replaces a newer one.

        Two scans of one catalog may save at once. The update only ever moves the time
        forward, and when both find no row and insert, the one that loses the race on
        the primary key tries again and takes the update path.
        """
        try:
            self._save_once(entity)
        except IntegrityError:
            self._save_once(entity)

    def _save_once(self, entity: CatalogDiscovery) -> None:
        at = entity.last_discovered_at
        forward = update(t).where(t.c.catalog == entity.catalog, t.c.last_discovered_at < at)
        with self._engine.begin() as conn:
            if conn.execute(forward.values(last_discovered_at=at)).rowcount:
                return
            if conn.execute(select(t.c.catalog).where(t.c.catalog == entity.catalog)).first() is not None:
                return
            conn.execute(insert(t).values(**CatalogDiscoveryRowMapper.to_values(entity)))

    def get(self, entity_id: EntityId) -> CatalogDiscovery | None:
        """Return the catalog's record, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.catalog == entity_id.value)).first()
        return None if row is None else CatalogDiscoveryRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[CatalogDiscovery]:
        """Return every record, by catalog name."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.catalog)).all()
        return [CatalogDiscoveryRowMapper.to_aggregate(r._mapping) for r in rows]
