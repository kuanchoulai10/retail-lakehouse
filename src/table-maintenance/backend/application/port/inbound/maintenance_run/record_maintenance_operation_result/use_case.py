"""Define the RecordMaintenanceOperationResultUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.maintenance_run.record_maintenance_operation_result.input import (
    RecordMaintenanceOperationResultUseCaseInput,
)
from application.port.inbound.maintenance_run.record_maintenance_operation_result.output import (
    RecordMaintenanceOperationResultUseCaseOutput,
)
from base.use_case import UseCase


class RecordMaintenanceOperationResultUseCase(
    UseCase[
        RecordMaintenanceOperationResultUseCaseInput,
        RecordMaintenanceOperationResultUseCaseOutput,
    ]
):
    """Record the result of a maintenance operation attempt."""

    @abstractmethod
    def execute(
        self, request: RecordMaintenanceOperationResultUseCaseInput
    ) -> RecordMaintenanceOperationResultUseCaseOutput:
        """Record the result of a maintenance operation attempt."""
