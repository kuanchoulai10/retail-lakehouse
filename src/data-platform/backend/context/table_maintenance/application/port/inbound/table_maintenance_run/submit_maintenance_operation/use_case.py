"""Define the SubmitMaintenanceOperationUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.submit_maintenance_operation.input import (  # noqa: E501
    SubmitMaintenanceOperationUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.submit_maintenance_operation.output import (  # noqa: E501
    SubmitMaintenanceOperationUseCaseOutput,
)


class SubmitMaintenanceOperationUseCase(
    UseCase[SubmitMaintenanceOperationUseCaseInput, SubmitMaintenanceOperationUseCaseOutput]
):
    """Submit one attempt of a maintenance operation to Spark."""

    @abstractmethod
    def execute(self, request: SubmitMaintenanceOperationUseCaseInput) -> SubmitMaintenanceOperationUseCaseOutput:
        """Submit one attempt of a maintenance operation to Spark."""
