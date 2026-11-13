"""Catalog discovery domain vocabulary: when discovery last scanned a whole catalog."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.catalog_discovery.catalog_discovery import (
    CatalogDiscovery,
)
from context.table_maintenance.application.domain.model.catalog_discovery.catalog_discovery_id import (
    CatalogDiscoveryId,
)

__all__ = [
    "CatalogDiscovery",
    "CatalogDiscoveryId",
]
