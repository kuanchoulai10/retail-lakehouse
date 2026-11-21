"""Define the InMemoryCatalogDiscoveriesRepo test fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.catalog_discovery import CatalogDiscoveriesRepo

if TYPE_CHECKING:
    from base import EntityId
    from context.table_maintenance.application.port.outbound.catalog_discovery import CatalogDiscovery


class InMemoryCatalogDiscoveriesRepo(CatalogDiscoveriesRepo):
    """Keep catalog discoveries in a dict keyed by catalog name, storing copies so saves are explicit.

    A save moves the stored scan time and failure each only forward, on its own, as the SQL repository does.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, CatalogDiscovery] = {}

    def create(self, entity: CatalogDiscovery) -> CatalogDiscovery:
        """Insert or replace the record."""
        self.save(entity)
        return entity

    def save(self, entity: CatalogDiscovery) -> None:
        """Insert the record, or move each of its times forward; an older one never replaces a newer one."""
        stored = self.items.get(entity.id.value)
        if stored is None:
            self.items[entity.id.value] = entity.model_copy()
            return
        if entity.last_discovered_at is not None:
            stored.record(entity.last_discovered_at)
        if entity.last_failure is not None:
            stored.record_failure(entity.last_failure)

    def get(self, entity_id: EntityId) -> CatalogDiscovery | None:
        """Return a copy of the record, or None."""
        found = self.items.get(entity_id.value)
        return None if found is None else found.model_copy()

    def list_all(self) -> list[CatalogDiscovery]:
        """Return every record, by catalog name."""
        return [self.items[k].model_copy() for k in sorted(self.items)]
