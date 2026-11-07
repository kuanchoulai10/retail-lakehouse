"""Inbound ports for the discovery group."""

from __future__ import annotations

from application.port.inbound.table_discovery_settings.get_table_discovery_settings.input import (
    GetTableDiscoverySettingsUseCaseInput,
)
from application.port.inbound.table_discovery_settings.get_table_discovery_settings.output import (
    GetTableDiscoverySettingsUseCaseOutput,
)
from application.port.inbound.table_discovery_settings.get_table_discovery_settings.use_case import (
    GetTableDiscoverySettingsUseCase,
)
from application.port.inbound.table_discovery_settings.update_table_discovery_settings.input import (
    UpdateTableDiscoverySettingsUseCaseInput,
)
from application.port.inbound.table_discovery_settings.update_table_discovery_settings.output import (
    UpdateTableDiscoverySettingsUseCaseOutput,
)
from application.port.inbound.table_discovery_settings.update_table_discovery_settings.use_case import (
    UpdateTableDiscoverySettingsUseCase,
)

__all__ = [
    "GetTableDiscoverySettingsUseCase",
    "GetTableDiscoverySettingsUseCaseInput",
    "GetTableDiscoverySettingsUseCaseOutput",
    "UpdateTableDiscoverySettingsUseCase",
    "UpdateTableDiscoverySettingsUseCaseInput",
    "UpdateTableDiscoverySettingsUseCaseOutput",
]
