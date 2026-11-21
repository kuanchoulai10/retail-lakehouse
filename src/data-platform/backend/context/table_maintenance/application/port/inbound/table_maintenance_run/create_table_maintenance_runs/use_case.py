"""Define the CreateTableMaintenanceRunsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.create_table_maintenance_runs.input import (  # noqa: E501
    CreateTableMaintenanceRunsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.create_table_maintenance_runs.output import (  # noqa: E501
    CreateTableMaintenanceRunsUseCaseOutput,
)


class CreateTableMaintenanceRunsUseCase(
    UseCase[CreateTableMaintenanceRunsUseCaseInput, CreateTableMaintenanceRunsUseCaseOutput]
):
    """Create the maintenance runs of one plan, all or none."""

    @abstractmethod
    def execute(self, request: CreateTableMaintenanceRunsUseCaseInput) -> CreateTableMaintenanceRunsUseCaseOutput:
        """Create the maintenance runs of one plan, all or none."""
