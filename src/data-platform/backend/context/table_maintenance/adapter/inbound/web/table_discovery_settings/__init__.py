"""Web adapter for the discovery group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_discovery_settings.dto import (
    CoveredCatalogsApiResponse,
    ScanDiscoveryApiRequest,
    ScanDiscoveryApiResponse,
    TableDiscoverySettingsApiResponse,
    UpdateTableDiscoverySettingsApiRequest,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_settings.router import (
    router,
)

__all__ = [
    "CoveredCatalogsApiResponse",
    "ScanDiscoveryApiRequest",
    "ScanDiscoveryApiResponse",
    "TableDiscoverySettingsApiResponse",
    "UpdateTableDiscoverySettingsApiRequest",
    "router",
]
