"""Define the ListMaintenanceRunsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.maintenance_run.list_maintenance_runs.input import (
    ListMaintenanceRunsUseCaseInput,
)
from application.port.inbound.maintenance_run.list_maintenance_runs.output import (
    ListMaintenanceRunsUseCaseOutput,
)
from base.use_case import UseCase


class ListMaintenanceRunsUseCase(
    UseCase[ListMaintenanceRunsUseCaseInput, ListMaintenanceRunsUseCaseOutput]
):
    """List the maintenance runs of a table."""

    @abstractmethod
    def execute(
        self, request: ListMaintenanceRunsUseCaseInput
    ) -> ListMaintenanceRunsUseCaseOutput:
        """List the maintenance runs of a table."""
