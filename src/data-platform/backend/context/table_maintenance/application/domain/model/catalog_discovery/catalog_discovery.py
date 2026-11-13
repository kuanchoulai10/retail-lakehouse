"""Define the CatalogDiscovery aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.catalog_discovery.catalog_discovery_id import (
    CatalogDiscoveryId,
)


class CatalogDiscovery(AggregateRoot[CatalogDiscoveryId]):
    """Remember when discovery last scanned one whole catalog.

    A catalog-wide scan sees every live table of the catalog, so its time is the
    last time each of them was discovered; recording it once per scan spares
    saving every table on every scan. A scan of one namespace is not recorded,
    since it does not see the rest of the catalog.
    """

    id: CatalogDiscoveryId
    last_discovered_at: datetime

    @model_validator(mode="after")
    def _names_a_catalog(self) -> CatalogDiscovery:
        if not self.id.value:
            raise ValueError("a catalog discovery needs a catalog name")
        return self

    @classmethod
    def first(cls, catalog: str, at: datetime) -> CatalogDiscovery:
        """Record the first scan of ``catalog``, which started at ``at``."""
        return cls(id=CatalogDiscoveryId(catalog), last_discovered_at=at)

    @property
    def catalog(self) -> str:
        """Return the name of the catalog scanned."""
        return self.id.value

    def record(self, at: datetime) -> None:
        """Record a scan that started at ``at``; the time never moves back."""
        self.last_discovered_at = max(self.last_discovered_at, at)
