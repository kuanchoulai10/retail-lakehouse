"""Define the GetMaintenanceRunUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.maintenance_run.get_maintenance_run.input import (
    GetMaintenanceRunUseCaseInput,
)
from application.port.inbound.maintenance_run.get_maintenance_run.output import (
    GetMaintenanceRunUseCaseOutput,
)
from base.use_case import UseCase


class GetMaintenanceRunUseCase(
    UseCase[GetMaintenanceRunUseCaseInput, GetMaintenanceRunUseCaseOutput]
):
    """Get one maintenance run."""

    @abstractmethod
    def execute(
        self, request: GetMaintenanceRunUseCaseInput
    ) -> GetMaintenanceRunUseCaseOutput:
        """Get one maintenance run."""
