"""Define the GetTableDiscoverySettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_discovery_settings.get_table_discovery_settings.input import (
    GetTableDiscoverySettingsUseCaseInput,
)
from application.port.inbound.table_discovery_settings.get_table_discovery_settings.output import (
    GetTableDiscoverySettingsUseCaseOutput,
)
from base.use_case import UseCase


class GetTableDiscoverySettingsUseCase(
    UseCase[
        GetTableDiscoverySettingsUseCaseInput, GetTableDiscoverySettingsUseCaseOutput
    ]
):
    """Get the discovery switch."""

    @abstractmethod
    def execute(
        self, request: GetTableDiscoverySettingsUseCaseInput
    ) -> GetTableDiscoverySettingsUseCaseOutput:
        """Get the discovery switch."""
