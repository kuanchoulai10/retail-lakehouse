"""Define the GetMaintenanceJobProcessesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_maintenance_job_processes.input import (  # noqa: E501
    GetMaintenanceJobProcessesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_maintenance_job_processes.output import (  # noqa: E501
    GetMaintenanceJobProcessesUseCaseOutput,
)


class GetMaintenanceJobProcessesUseCase(
    UseCase[GetMaintenanceJobProcessesUseCaseInput, GetMaintenanceJobProcessesUseCaseOutput]
):
    """Get the live processes of one maintenance job attempt."""

    @abstractmethod
    def execute(self, request: GetMaintenanceJobProcessesUseCaseInput) -> GetMaintenanceJobProcessesUseCaseOutput:
        """Get the live processes of one maintenance job attempt."""
