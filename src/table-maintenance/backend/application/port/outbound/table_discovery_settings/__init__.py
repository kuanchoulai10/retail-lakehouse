"""Outbound ports for the discovery group."""

from __future__ import annotations

from application.domain.model.table_discovery_settings import (
    TableDiscoverySettings,
    TableDiscoverySettingsId,
)
from application.port.outbound.table_discovery_settings.table_discovery_settings_repo import (
    TableDiscoverySettingsRepo,
)
from application.port.outbound.table_discovery_settings.update_table_discovery_schedule.gateway import (
    UpdateTableDiscoveryScheduleGateway,
)
from application.port.outbound.table_discovery_settings.update_table_discovery_schedule.input import (
    UpdateTableDiscoveryScheduleGatewayInput,
)

__all__ = [
    "TableDiscoverySettingsId",
    "TableDiscoverySettings",
    "TableDiscoverySettingsRepo",
    "UpdateTableDiscoveryScheduleGateway",
    "UpdateTableDiscoveryScheduleGatewayInput",
]
