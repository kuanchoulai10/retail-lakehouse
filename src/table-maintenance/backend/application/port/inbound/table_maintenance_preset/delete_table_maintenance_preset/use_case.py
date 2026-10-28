"""Define the DeleteTableMaintenancePresetUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset.input import (
    DeleteTableMaintenancePresetUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset.output import (
    DeleteTableMaintenancePresetUseCaseOutput,
)
from base import UseCase


class DeleteTableMaintenancePresetUseCase(
    UseCase[
        DeleteTableMaintenancePresetUseCaseInput,
        DeleteTableMaintenancePresetUseCaseOutput,
    ]
):
    """Delete a table maintenance preset that no rule references."""

    @abstractmethod
    def execute(
        self, request: DeleteTableMaintenancePresetUseCaseInput
    ) -> DeleteTableMaintenancePresetUseCaseOutput:
        """Delete a table maintenance preset that no rule references."""
