"""Define the UpdateTableSettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.update_table_settings.input import (
    UpdateTableSettingsUseCaseInput,
)
from application.port.inbound.table.update_table_settings.output import (
    UpdateTableSettingsUseCaseOutput,
)
from base import UseCase


class UpdateTableSettingsUseCase(
    UseCase[UpdateTableSettingsUseCaseInput, UpdateTableSettingsUseCaseOutput]
):
    """Replace a table's settings."""

    @abstractmethod
    def execute(
        self, request: UpdateTableSettingsUseCaseInput
    ) -> UpdateTableSettingsUseCaseOutput:
        """Replace a table's settings."""
