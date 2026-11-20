"""Define the GetPlatformSettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_platform_settings.input import (
    GetPlatformSettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_platform_settings.output import (
    GetPlatformSettingsUseCaseOutput,
)


class GetPlatformSettingsUseCase(UseCase[GetPlatformSettingsUseCaseInput, GetPlatformSettingsUseCaseOutput]):
    """Read the platform-level settings the running component was started with, grouped by theme."""

    @abstractmethod
    def execute(self, request: GetPlatformSettingsUseCaseInput) -> GetPlatformSettingsUseCaseOutput:
        """Read the platform settings."""
