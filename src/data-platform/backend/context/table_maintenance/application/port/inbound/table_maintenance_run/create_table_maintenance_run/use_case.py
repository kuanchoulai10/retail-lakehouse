"""Define the CreateTableMaintenanceRunUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table_maintenance_run.create_table_maintenance_run.input import (
    CreateTableMaintenanceRunUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.create_table_maintenance_run.output import (
    CreateTableMaintenanceRunUseCaseOutput,
)
from base import UseCase


class CreateTableMaintenanceRunUseCase(
    UseCase[
        CreateTableMaintenanceRunUseCaseInput, CreateTableMaintenanceRunUseCaseOutput
    ]
):
    """Create a maintenance run."""

    @abstractmethod
    def execute(
        self, request: CreateTableMaintenanceRunUseCaseInput
    ) -> CreateTableMaintenanceRunUseCaseOutput:
        """Create a maintenance run."""
