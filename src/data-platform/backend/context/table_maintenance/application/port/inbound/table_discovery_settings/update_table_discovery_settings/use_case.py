"""Define the UpdateTableDiscoverySettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_settings.update_table_discovery_settings.input import (
    UpdateTableDiscoverySettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings.update_table_discovery_settings.output import (
    UpdateTableDiscoverySettingsUseCaseOutput,
)


class UpdateTableDiscoverySettingsUseCase(
    UseCase[
        UpdateTableDiscoverySettingsUseCaseInput,
        UpdateTableDiscoverySettingsUseCaseOutput,
    ]
):
    """Turn discovery on or off."""

    @abstractmethod
    def execute(self, request: UpdateTableDiscoverySettingsUseCaseInput) -> UpdateTableDiscoverySettingsUseCaseOutput:
        """Turn discovery on or off."""
