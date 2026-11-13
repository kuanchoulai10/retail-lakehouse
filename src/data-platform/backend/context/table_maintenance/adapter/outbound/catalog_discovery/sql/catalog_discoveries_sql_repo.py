"""Define the CatalogDiscoveriesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select

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
        """Replace the catalog's row in one transaction."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.catalog == entity.catalog))
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
