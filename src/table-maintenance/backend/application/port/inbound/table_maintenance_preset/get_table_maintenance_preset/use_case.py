"""Define the GetTableMaintenancePresetUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_maintenance_preset.get_table_maintenance_preset.input import (
    GetTableMaintenancePresetUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.get_table_maintenance_preset.output import (
    GetTableMaintenancePresetUseCaseOutput,
)
from base import UseCase


class GetTableMaintenancePresetUseCase(
    UseCase[
        GetTableMaintenancePresetUseCaseInput, GetTableMaintenancePresetUseCaseOutput
    ]
):
    """Get one table maintenance preset."""

    @abstractmethod
    def execute(
        self, request: GetTableMaintenancePresetUseCaseInput
    ) -> GetTableMaintenancePresetUseCaseOutput:
        """Get one table maintenance preset."""
