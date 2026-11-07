"""Define the DeleteMaintenanceJobUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.delete_maintenance_job.input import (
    DeleteMaintenanceJobUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.delete_maintenance_job.output import (
    DeleteMaintenanceJobUseCaseOutput,
)


class DeleteMaintenanceJobUseCase(UseCase[DeleteMaintenanceJobUseCaseInput, DeleteMaintenanceJobUseCaseOutput]):
    """Delete a Spark maintenance job."""

    @abstractmethod
    def execute(self, request: DeleteMaintenanceJobUseCaseInput) -> DeleteMaintenanceJobUseCaseOutput:
        """Delete a Spark maintenance job."""
