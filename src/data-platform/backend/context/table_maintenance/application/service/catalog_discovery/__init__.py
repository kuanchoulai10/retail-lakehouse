"""Catalog discovery use case implementations.

Syncing the discovered tables records a catalog's discovery, and the table
listing reads it, both through ``CatalogDiscoveriesRepo``; this group lists
the scanned catalogs with their scan state.
"""

from __future__ import annotations

from context.table_maintenance.application.service.catalog_discovery.list_scanned_catalogs import (
    ListScannedCatalogsService,
)

__all__ = ["ListScannedCatalogsService"]
