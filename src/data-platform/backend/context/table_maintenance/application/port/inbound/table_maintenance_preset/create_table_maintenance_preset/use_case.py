"""Define the CreateTableMaintenancePresetUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table_maintenance_preset.create_table_maintenance_preset.input import (
    CreateTableMaintenancePresetUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset.create_table_maintenance_preset.output import (
    CreateTableMaintenancePresetUseCaseOutput,
)
from base import UseCase


class CreateTableMaintenancePresetUseCase(
    UseCase[
        CreateTableMaintenancePresetUseCaseInput,
        CreateTableMaintenancePresetUseCaseOutput,
    ]
):
    """Create a table maintenance preset."""

    @abstractmethod
    def execute(
        self, request: CreateTableMaintenancePresetUseCaseInput
    ) -> CreateTableMaintenancePresetUseCaseOutput:
        """Create a table maintenance preset."""
