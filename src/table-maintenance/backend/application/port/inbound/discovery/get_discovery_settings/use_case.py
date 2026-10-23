"""Define the GetDiscoverySettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery.get_discovery_settings.input import (
    GetDiscoverySettingsUseCaseInput,
)
from application.port.inbound.discovery.get_discovery_settings.output import (
    GetDiscoverySettingsUseCaseOutput,
)
from base.use_case import UseCase


class GetDiscoverySettingsUseCase(
    UseCase[GetDiscoverySettingsUseCaseInput, GetDiscoverySettingsUseCaseOutput]
):
    """Get the discovery switch."""

    @abstractmethod
    def execute(
        self, request: GetDiscoverySettingsUseCaseInput
    ) -> GetDiscoverySettingsUseCaseOutput:
        """Get the discovery switch."""
