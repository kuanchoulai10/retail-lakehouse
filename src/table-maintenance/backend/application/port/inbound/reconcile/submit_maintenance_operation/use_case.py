"""Define the SubmitMaintenanceOperationUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.reconcile.submit_maintenance_operation.input import (
    SubmitMaintenanceOperationUseCaseInput,
)
from application.port.inbound.reconcile.submit_maintenance_operation.output import (
    SubmitMaintenanceOperationUseCaseOutput,
)
from base.use_case import UseCase


class SubmitMaintenanceOperationUseCase(
    UseCase[
        SubmitMaintenanceOperationUseCaseInput, SubmitMaintenanceOperationUseCaseOutput
    ]
):
    """Submit one attempt of a maintenance operation to Spark."""

    @abstractmethod
    def execute(
        self, request: SubmitMaintenanceOperationUseCaseInput
    ) -> SubmitMaintenanceOperationUseCaseOutput:
        """Submit one attempt of a maintenance operation to Spark."""
