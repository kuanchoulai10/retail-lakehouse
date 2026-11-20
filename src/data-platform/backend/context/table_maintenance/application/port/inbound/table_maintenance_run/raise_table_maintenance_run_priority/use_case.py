"""Define the RaiseTableMaintenanceRunPriorityUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.raise_table_maintenance_run_priority.input import (  # noqa: E501
    RaiseTableMaintenanceRunPriorityUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.raise_table_maintenance_run_priority.output import (  # noqa: E501
    RaiseTableMaintenanceRunPriorityUseCaseOutput,
)


class RaiseTableMaintenanceRunPriorityUseCase(
    UseCase[RaiseTableMaintenanceRunPriorityUseCaseInput, RaiseTableMaintenanceRunPriorityUseCaseOutput]
):
    """Raise the priority of a maintenance run, only upward."""

    @abstractmethod
    def execute(
        self, request: RaiseTableMaintenanceRunPriorityUseCaseInput
    ) -> RaiseTableMaintenanceRunPriorityUseCaseOutput:
        """Raise the priority of a maintenance run, only upward."""
