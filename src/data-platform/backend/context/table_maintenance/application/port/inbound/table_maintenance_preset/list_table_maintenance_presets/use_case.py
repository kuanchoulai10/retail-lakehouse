"""Define the ListTableMaintenancePresetsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_preset.list_table_maintenance_presets.input import (
    ListTableMaintenancePresetsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset.list_table_maintenance_presets.output import (
    ListTableMaintenancePresetsUseCaseOutput,
)


class ListTableMaintenancePresetsUseCase(
    UseCase[
        ListTableMaintenancePresetsUseCaseInput,
        ListTableMaintenancePresetsUseCaseOutput,
    ]
):
    """List all table maintenance presets."""

    @abstractmethod
    def execute(self, request: ListTableMaintenancePresetsUseCaseInput) -> ListTableMaintenancePresetsUseCaseOutput:
        """List all table maintenance presets."""
