"""Define the TriggerTableMaintenanceUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.trigger_table_maintenance.input import (
    TriggerTableMaintenanceUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.trigger_table_maintenance.output import (
    TriggerTableMaintenanceUseCaseOutput,
)
from base import UseCase


class TriggerTableMaintenanceUseCase(
    UseCase[TriggerTableMaintenanceUseCaseInput, TriggerTableMaintenanceUseCaseOutput]
):
    """Trigger maintenance operations on a table now."""

    @abstractmethod
    def execute(
        self, request: TriggerTableMaintenanceUseCaseInput
    ) -> TriggerTableMaintenanceUseCaseOutput:
        """Trigger maintenance operations on a table now."""
