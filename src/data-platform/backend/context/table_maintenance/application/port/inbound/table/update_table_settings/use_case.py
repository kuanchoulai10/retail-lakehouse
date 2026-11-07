"""Define the UpdateTableSettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.update_table_settings.input import (
    UpdateTableSettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.update_table_settings.output import (
    UpdateTableSettingsUseCaseOutput,
)


class UpdateTableSettingsUseCase(UseCase[UpdateTableSettingsUseCaseInput, UpdateTableSettingsUseCaseOutput]):
    """Replace a table's settings."""

    @abstractmethod
    def execute(self, request: UpdateTableSettingsUseCaseInput) -> UpdateTableSettingsUseCaseOutput:
        """Replace a table's settings."""
