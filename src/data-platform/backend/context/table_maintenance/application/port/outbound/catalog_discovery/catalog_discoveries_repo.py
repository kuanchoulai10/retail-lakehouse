"""Define the CatalogDiscoveriesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from base import Repository
from context.table_maintenance.application.domain.model.catalog_discovery import CatalogDiscovery


class CatalogDiscoveriesRepo(Repository[CatalogDiscovery]):
    """Persist when discovery last scanned each catalog, one record per catalog."""

    @abstractmethod
    def save(self, entity: CatalogDiscovery) -> None:
        """Insert the record, or move the stored one's time forward to it; an older time changes nothing."""
