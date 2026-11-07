"""Define the RecordTableMaintenanceOperationResultUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table_maintenance_run.record_table_maintenance_operation_result.input import (
    RecordTableMaintenanceOperationResultUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.record_table_maintenance_operation_result.output import (
    RecordTableMaintenanceOperationResultUseCaseOutput,
)
from base import UseCase


class RecordTableMaintenanceOperationResultUseCase(
    UseCase[
        RecordTableMaintenanceOperationResultUseCaseInput,
        RecordTableMaintenanceOperationResultUseCaseOutput,
    ]
):
    """Record the result of a maintenance operation attempt."""

    @abstractmethod
    def execute(
        self, request: RecordTableMaintenanceOperationResultUseCaseInput
    ) -> RecordTableMaintenanceOperationResultUseCaseOutput:
        """Record the result of a maintenance operation attempt."""
