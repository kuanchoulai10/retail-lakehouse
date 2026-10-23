"""Define the UpdateDiscoverySettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery.update_discovery_settings.input import (
    UpdateDiscoverySettingsUseCaseInput,
)
from application.port.inbound.discovery.update_discovery_settings.output import (
    UpdateDiscoverySettingsUseCaseOutput,
)
from base.use_case import UseCase


class UpdateDiscoverySettingsUseCase(
    UseCase[UpdateDiscoverySettingsUseCaseInput, UpdateDiscoverySettingsUseCaseOutput]
):
    """Turn discovery on or off."""

    @abstractmethod
    def execute(
        self, request: UpdateDiscoverySettingsUseCaseInput
    ) -> UpdateDiscoverySettingsUseCaseOutput:
        """Turn discovery on or off."""
