"""Web adapter for the catalog_discovery group: the catalogs discovery scans."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.catalog_discovery.dto import (
    CatalogScanFailureApiResponse,
    ScannedCatalogApiResponse,
    ScannedCatalogsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.catalog_discovery.router import router

__all__ = [
    "CatalogScanFailureApiResponse",
    "ScannedCatalogApiResponse",
    "ScannedCatalogsApiResponse",
    "router",
]
