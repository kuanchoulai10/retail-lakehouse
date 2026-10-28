"""Discovery settings domain vocabulary."""

from __future__ import annotations

from application.domain.model.table_discovery_settings.table_discovery_settings import (
    GLOBAL_ID,
    TableDiscoverySettings,
)
from application.domain.model.table_discovery_settings.table_discovery_settings_id import (
    TableDiscoverySettingsId,
)

__all__ = [
    "GLOBAL_ID",
    "TableDiscoverySettings",
    "TableDiscoverySettingsId",
]
