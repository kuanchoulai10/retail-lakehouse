"""Discovery switch use case implementations."""

from __future__ import annotations

from application.service.table_discovery_settings.get_table_discovery_settings import (
    GetTableDiscoverySettingsService,
)
from application.service.table_discovery_settings.update_table_discovery_settings import (
    UpdateTableDiscoverySettingsService,
)

__all__ = [
    "GetTableDiscoverySettingsService",
    "UpdateTableDiscoverySettingsService",
]
