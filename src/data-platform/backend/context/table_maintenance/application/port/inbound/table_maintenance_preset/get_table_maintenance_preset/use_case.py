"""Define the GetTableMaintenancePresetUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_preset.get_table_maintenance_preset.input import (  # noqa: E501
    GetTableMaintenancePresetUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset.get_table_maintenance_preset.output import (  # noqa: E501
    GetTableMaintenancePresetUseCaseOutput,
)


class GetTableMaintenancePresetUseCase(
    UseCase[GetTableMaintenancePresetUseCaseInput, GetTableMaintenancePresetUseCaseOutput]
):
    """Get one table maintenance preset."""

    @abstractmethod
    def execute(self, request: GetTableMaintenancePresetUseCaseInput) -> GetTableMaintenancePresetUseCaseOutput:
        """Get one table maintenance preset."""
