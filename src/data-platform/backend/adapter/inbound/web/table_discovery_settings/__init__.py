"""Web adapter for the discovery group."""

from __future__ import annotations

from adapter.inbound.web.table_discovery_settings.dto import (
    ScanDiscoveryApiRequest,
    ScanDiscoveryApiResponse,
    TableDiscoverySettingsApiResponse,
    UpdateTableDiscoverySettingsApiRequest,
)
from adapter.inbound.web.table_discovery_settings.router import router

__all__ = [
    "ScanDiscoveryApiRequest",
    "ScanDiscoveryApiResponse",
    "TableDiscoverySettingsApiResponse",
    "UpdateTableDiscoverySettingsApiRequest",
    "router",
]
