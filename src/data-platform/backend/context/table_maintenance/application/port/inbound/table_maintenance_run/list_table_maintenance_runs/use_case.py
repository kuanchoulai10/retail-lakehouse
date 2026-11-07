"""Define the ListTableMaintenanceRunsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.list_table_maintenance_runs.input import (
    ListTableMaintenanceRunsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.list_table_maintenance_runs.output import (
    ListTableMaintenanceRunsUseCaseOutput,
)


class ListTableMaintenanceRunsUseCase(
    UseCase[ListTableMaintenanceRunsUseCaseInput, ListTableMaintenanceRunsUseCaseOutput]
):
    """List the maintenance runs of a table."""

    @abstractmethod
    def execute(self, request: ListTableMaintenanceRunsUseCaseInput) -> ListTableMaintenanceRunsUseCaseOutput:
        """List the maintenance runs of a table."""
