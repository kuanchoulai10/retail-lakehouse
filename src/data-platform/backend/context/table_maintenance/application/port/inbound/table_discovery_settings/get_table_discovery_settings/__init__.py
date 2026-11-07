"""Get the discovery switch."""

from context.table_maintenance.application.port.inbound.table_discovery_settings.get_table_discovery_settings.input import (
    GetTableDiscoverySettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings.get_table_discovery_settings.output import (
    GetTableDiscoverySettingsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings.get_table_discovery_settings.use_case import (
    GetTableDiscoverySettingsUseCase,
)

__all__ = [
    "GetTableDiscoverySettingsUseCase",
    "GetTableDiscoverySettingsUseCaseInput",
    "GetTableDiscoverySettingsUseCaseOutput",
]
