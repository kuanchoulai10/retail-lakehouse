"""Define the CreateMaintenanceRunUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.maintenance_run.create_maintenance_run.input import (
    CreateMaintenanceRunUseCaseInput,
)
from application.port.inbound.maintenance_run.create_maintenance_run.output import (
    CreateMaintenanceRunUseCaseOutput,
)
from base.use_case import UseCase


class CreateMaintenanceRunUseCase(
    UseCase[CreateMaintenanceRunUseCaseInput, CreateMaintenanceRunUseCaseOutput]
):
    """Create a maintenance run."""

    @abstractmethod
    def execute(
        self, request: CreateMaintenanceRunUseCaseInput
    ) -> CreateMaintenanceRunUseCaseOutput:
        """Create a maintenance run."""
