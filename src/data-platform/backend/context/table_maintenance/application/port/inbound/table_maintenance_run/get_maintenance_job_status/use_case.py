"""Define the GetMaintenanceJobStatusUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_maintenance_job_status.input import (
    GetMaintenanceJobStatusUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_maintenance_job_status.output import (
    GetMaintenanceJobStatusUseCaseOutput,
)


class GetMaintenanceJobStatusUseCase(
    UseCase[GetMaintenanceJobStatusUseCaseInput, GetMaintenanceJobStatusUseCaseOutput]
):
    """Get the state of a Spark maintenance job."""

    @abstractmethod
    def execute(self, request: GetMaintenanceJobStatusUseCaseInput) -> GetMaintenanceJobStatusUseCaseOutput:
        """Get the state of a Spark maintenance job."""
