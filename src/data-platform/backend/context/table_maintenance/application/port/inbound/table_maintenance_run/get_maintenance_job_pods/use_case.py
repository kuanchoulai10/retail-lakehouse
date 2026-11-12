"""Define the GetMaintenanceJobPodsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_maintenance_job_pods.input import (
    GetMaintenanceJobPodsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.get_maintenance_job_pods.output import (
    GetMaintenanceJobPodsUseCaseOutput,
)


class GetMaintenanceJobPodsUseCase(UseCase[GetMaintenanceJobPodsUseCaseInput, GetMaintenanceJobPodsUseCaseOutput]):
    """Get the live pods of one maintenance job attempt."""

    @abstractmethod
    def execute(self, request: GetMaintenanceJobPodsUseCaseInput) -> GetMaintenanceJobPodsUseCaseOutput:
        """Get the live pods of one maintenance job attempt."""
