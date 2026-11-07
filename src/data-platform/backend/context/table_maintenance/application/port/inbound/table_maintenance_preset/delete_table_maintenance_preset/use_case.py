"""Define the DeleteTableMaintenancePresetUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset.input import (  # noqa: E501
    DeleteTableMaintenancePresetUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset.output import (  # noqa: E501
    DeleteTableMaintenancePresetUseCaseOutput,
)


class DeleteTableMaintenancePresetUseCase(
    UseCase[
        DeleteTableMaintenancePresetUseCaseInput,
        DeleteTableMaintenancePresetUseCaseOutput,
    ]
):
    """Delete a table maintenance preset that no rule references."""

    @abstractmethod
    def execute(self, request: DeleteTableMaintenancePresetUseCaseInput) -> DeleteTableMaintenancePresetUseCaseOutput:
        """Delete a table maintenance preset that no rule references."""
