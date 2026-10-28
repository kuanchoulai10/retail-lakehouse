"""Define the UpdateTableMaintenancePresetUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_maintenance_preset.update_table_maintenance_preset.input import (
    UpdateTableMaintenancePresetUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.update_table_maintenance_preset.output import (
    UpdateTableMaintenancePresetUseCaseOutput,
)
from base import UseCase


class UpdateTableMaintenancePresetUseCase(
    UseCase[
        UpdateTableMaintenancePresetUseCaseInput,
        UpdateTableMaintenancePresetUseCaseOutput,
    ]
):
    """Rename a table maintenance preset or replace its settings."""

    @abstractmethod
    def execute(
        self, request: UpdateTableMaintenancePresetUseCaseInput
    ) -> UpdateTableMaintenancePresetUseCaseOutput:
        """Rename a table maintenance preset or replace its settings."""
