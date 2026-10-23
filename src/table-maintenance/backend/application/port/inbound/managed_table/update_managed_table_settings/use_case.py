"""Define the UpdateManagedTableSettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.update_managed_table_settings.input import (
    UpdateManagedTableSettingsUseCaseInput,
)
from application.port.inbound.managed_table.update_managed_table_settings.output import (
    UpdateManagedTableSettingsUseCaseOutput,
)
from base.use_case import UseCase


class UpdateManagedTableSettingsUseCase(
    UseCase[
        UpdateManagedTableSettingsUseCaseInput, UpdateManagedTableSettingsUseCaseOutput
    ]
):
    """Replace a managed table's settings."""

    @abstractmethod
    def execute(
        self, request: UpdateManagedTableSettingsUseCaseInput
    ) -> UpdateManagedTableSettingsUseCaseOutput:
        """Replace a managed table's settings."""
