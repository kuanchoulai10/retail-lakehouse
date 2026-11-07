"""Outbound ports for the discovery group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_discovery_settings import (
    GLOBAL_ID,
    TableDiscoverySettings,
    TableDiscoverySettingsId,
)
from context.table_maintenance.application.port.outbound.table_discovery_settings.table_discovery_settings_repo import (
    TableDiscoverySettingsRepo,
)
from context.table_maintenance.application.port.outbound.table_discovery_settings.update_table_discovery_schedule.gateway import (
    UpdateTableDiscoveryScheduleGateway,
)
from context.table_maintenance.application.port.outbound.table_discovery_settings.update_table_discovery_schedule.input import (
    UpdateTableDiscoveryScheduleGatewayInput,
)

__all__ = [
    "GLOBAL_ID",
    "TableDiscoverySettingsId",
    "TableDiscoverySettings",
    "TableDiscoverySettingsRepo",
    "UpdateTableDiscoveryScheduleGateway",
    "UpdateTableDiscoveryScheduleGatewayInput",
]
