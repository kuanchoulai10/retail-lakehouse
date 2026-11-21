"""Define the CatalogDiscoveriesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, or_, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.catalog_discovery.sql.catalog_discoveries_table import (
    catalog_discoveries_table as t,
)
from context.table_maintenance.adapter.outbound.catalog_discovery.sql.catalog_discovery_row_mapper import (
    CatalogDiscoveryRowMapper,
)
from context.table_maintenance.application.port.outbound.catalog_discovery import CatalogDiscoveriesRepo

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

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
        """Insert the catalog's row, or move each of its two times forward on its own; neither ever moves back.

        Two scans of one catalog may save at once. Each update only ever moves its own time
        forward (the scan time, or the failure with its reason and detail), and when both
        find no row and insert, the one that loses the race on the primary key tries again
        and takes the update path.
        """
        try:
            self._save_once(entity)
        except IntegrityError:
            self._save_once(entity)

    def _save_once(self, entity: CatalogDiscovery) -> None:
        with self._engine.begin() as conn:
            if conn.execute(select(t.c.catalog).where(t.c.catalog == entity.catalog)).first() is None:
                conn.execute(insert(t).values(**CatalogDiscoveryRowMapper.to_values(entity)))
                return
            self._move_scan_forward(conn, entity)
            self._move_failure_forward(conn, entity)

    @staticmethod
    def _move_scan_forward(conn: Connection, entity: CatalogDiscovery) -> None:
        at = entity.last_discovered_at
        if at is None:
            return
        older = or_(t.c.last_discovered_at.is_(None), t.c.last_discovered_at < at)
        conn.execute(update(t).where(t.c.catalog == entity.catalog, older).values(last_discovered_at=at))

    @staticmethod
    def _move_failure_forward(conn: Connection, entity: CatalogDiscovery) -> None:
        failure = entity.last_failure
        if failure is None:
            return
        older = or_(t.c.failed_at.is_(None), t.c.failed_at < failure.failed_at)
        conn.execute(
            update(t)
            .where(t.c.catalog == entity.catalog, older)
            .values(**CatalogDiscoveryRowMapper.failure_values(failure))
        )

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
