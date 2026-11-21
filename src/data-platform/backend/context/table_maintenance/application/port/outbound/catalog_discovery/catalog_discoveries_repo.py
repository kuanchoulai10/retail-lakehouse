"""Define the CatalogDiscoveriesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from base import Repository
from context.table_maintenance.application.domain.model.catalog_discovery import CatalogDiscovery


class CatalogDiscoveriesRepo(Repository[CatalogDiscovery]):
    """Persist when discovery last scanned each catalog, and last failed to, one record per catalog."""

    @abstractmethod
    def save(self, entity: CatalogDiscovery) -> None:
        """Insert the record, or move each of the stored times forward to the entity's on its own.

        The scan time and the failure each move only forward: an older one changes nothing, and
        moving one never touches the other.
        """
