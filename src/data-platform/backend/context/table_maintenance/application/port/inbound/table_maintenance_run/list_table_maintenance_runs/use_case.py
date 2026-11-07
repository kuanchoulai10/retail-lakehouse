"""Define the ListTableMaintenanceRunsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table_maintenance_run.list_table_maintenance_runs.input import (
    ListTableMaintenanceRunsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.list_table_maintenance_runs.output import (
    ListTableMaintenanceRunsUseCaseOutput,
)
from base import UseCase


class ListTableMaintenanceRunsUseCase(
    UseCase[ListTableMaintenanceRunsUseCaseInput, ListTableMaintenanceRunsUseCaseOutput]
):
    """List the maintenance runs of a table."""

    @abstractmethod
    def execute(
        self, request: ListTableMaintenanceRunsUseCaseInput
    ) -> ListTableMaintenanceRunsUseCaseOutput:
        """List the maintenance runs of a table."""
