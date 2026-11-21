"""Inbound ports for the catalog_discovery group.

Syncing the discovered tables records a catalog's discovery, and the table
listing reads it, both through ``CatalogDiscoveriesRepo``; listing the
scanned catalogs reports each one's scan state.
"""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.catalog_discovery.list_scanned_catalogs import (
    ListScannedCatalogsUseCase,
    ListScannedCatalogsUseCaseInput,
    ListScannedCatalogsUseCaseOutput,
)

__all__ = [
    "ListScannedCatalogsUseCase",
    "ListScannedCatalogsUseCaseInput",
    "ListScannedCatalogsUseCaseOutput",
]
