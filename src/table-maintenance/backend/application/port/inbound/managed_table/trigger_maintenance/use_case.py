"""Define the TriggerMaintenanceUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.trigger_maintenance.input import (
    TriggerMaintenanceUseCaseInput,
)
from application.port.inbound.managed_table.trigger_maintenance.output import (
    TriggerMaintenanceUseCaseOutput,
)
from base.use_case import UseCase


class TriggerMaintenanceUseCase(
    UseCase[TriggerMaintenanceUseCaseInput, TriggerMaintenanceUseCaseOutput]
):
    """Trigger maintenance operations on a table now."""

    @abstractmethod
    def execute(
        self, request: TriggerMaintenanceUseCaseInput
    ) -> TriggerMaintenanceUseCaseOutput:
        """Trigger maintenance operations on a table now."""
