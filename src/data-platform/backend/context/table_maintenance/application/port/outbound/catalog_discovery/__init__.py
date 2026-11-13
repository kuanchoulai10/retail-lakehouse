"""Outbound ports for the catalog_discovery group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
)
from context.table_maintenance.application.port.outbound.catalog_discovery.catalog_discoveries_repo import (
    CatalogDiscoveriesRepo,
)

__all__ = [
    "CatalogDiscoveriesRepo",
    "CatalogDiscovery",
    "CatalogDiscoveryId",
]
