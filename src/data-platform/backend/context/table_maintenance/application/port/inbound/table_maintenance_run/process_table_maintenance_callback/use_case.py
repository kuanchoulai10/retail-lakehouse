"""Define the ProcessTableMaintenanceCallbackUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.process_table_maintenance_callback.input import (
    ProcessTableMaintenanceCallbackUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.process_table_maintenance_callback.output import (
    ProcessTableMaintenanceCallbackUseCaseOutput,
)


class ProcessTableMaintenanceCallbackUseCase(
    UseCase[
        ProcessTableMaintenanceCallbackUseCaseInput,
        ProcessTableMaintenanceCallbackUseCaseOutput,
    ]
):
    """Forward a Spark job result callback to the workflow."""

    @abstractmethod
    def execute(
        self, request: ProcessTableMaintenanceCallbackUseCaseInput
    ) -> ProcessTableMaintenanceCallbackUseCaseOutput:
        """Forward a Spark job result callback to the workflow."""
