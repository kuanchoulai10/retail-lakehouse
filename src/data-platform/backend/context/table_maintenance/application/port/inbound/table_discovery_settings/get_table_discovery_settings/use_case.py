"""Define the GetTableDiscoverySettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_settings.get_table_discovery_settings.input import (
    GetTableDiscoverySettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings.get_table_discovery_settings.output import (
    GetTableDiscoverySettingsUseCaseOutput,
)


class GetTableDiscoverySettingsUseCase(
    UseCase[GetTableDiscoverySettingsUseCaseInput, GetTableDiscoverySettingsUseCaseOutput]
):
    """Get the discovery switch."""

    @abstractmethod
    def execute(self, request: GetTableDiscoverySettingsUseCaseInput) -> GetTableDiscoverySettingsUseCaseOutput:
        """Get the discovery switch."""
