"""Define the GetMaintenanceJobStatusUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_maintenance_run.get_maintenance_job_status.input import (
    GetMaintenanceJobStatusUseCaseInput,
)
from application.port.inbound.table_maintenance_run.get_maintenance_job_status.output import (
    GetMaintenanceJobStatusUseCaseOutput,
)
from base import UseCase


class GetMaintenanceJobStatusUseCase(
    UseCase[GetMaintenanceJobStatusUseCaseInput, GetMaintenanceJobStatusUseCaseOutput]
):
    """Get the state of a Spark maintenance job."""

    @abstractmethod
    def execute(
        self, request: GetMaintenanceJobStatusUseCaseInput
    ) -> GetMaintenanceJobStatusUseCaseOutput:
        """Get the state of a Spark maintenance job."""
