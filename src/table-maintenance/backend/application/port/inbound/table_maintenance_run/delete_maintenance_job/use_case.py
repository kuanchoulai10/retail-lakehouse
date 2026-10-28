"""Define the DeleteMaintenanceJobUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_maintenance_run.delete_maintenance_job.input import (
    DeleteMaintenanceJobUseCaseInput,
)
from application.port.inbound.table_maintenance_run.delete_maintenance_job.output import (
    DeleteMaintenanceJobUseCaseOutput,
)
from base.use_case import UseCase


class DeleteMaintenanceJobUseCase(
    UseCase[DeleteMaintenanceJobUseCaseInput, DeleteMaintenanceJobUseCaseOutput]
):
    """Delete a Spark maintenance job."""

    @abstractmethod
    def execute(
        self, request: DeleteMaintenanceJobUseCaseInput
    ) -> DeleteMaintenanceJobUseCaseOutput:
        """Delete a Spark maintenance job."""
