"""Define the ProcessMaintenanceCallbackUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.maintenance_run.process_maintenance_callback.input import (
    ProcessMaintenanceCallbackUseCaseInput,
)
from application.port.inbound.maintenance_run.process_maintenance_callback.output import (
    ProcessMaintenanceCallbackUseCaseOutput,
)
from base.use_case import UseCase


class ProcessMaintenanceCallbackUseCase(
    UseCase[
        ProcessMaintenanceCallbackUseCaseInput, ProcessMaintenanceCallbackUseCaseOutput
    ]
):
    """Forward a Spark job result callback to the workflow."""

    @abstractmethod
    def execute(
        self, request: ProcessMaintenanceCallbackUseCaseInput
    ) -> ProcessMaintenanceCallbackUseCaseOutput:
        """Forward a Spark job result callback to the workflow."""
