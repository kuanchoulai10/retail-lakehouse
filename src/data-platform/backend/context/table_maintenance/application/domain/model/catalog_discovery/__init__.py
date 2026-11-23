"""Catalog discovery domain vocabulary: when discovery last scanned a whole catalog, and when it could not."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.catalog_discovery.catalog_discovery import (
    CatalogDiscovery,
)
from context.table_maintenance.application.domain.model.catalog_discovery.catalog_scan_failure import (
    CatalogScanFailure,
)
from context.table_maintenance.application.domain.model.catalog_discovery.catalog_scan_failure_reason import (
    CatalogScanFailureReason,
)

__all__ = [
    "CatalogDiscovery",
    "CatalogScanFailure",
    "CatalogScanFailureReason",
]
