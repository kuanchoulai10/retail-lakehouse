"""Define the GetTableMaintenanceRunUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_maintenance_run.get_table_maintenance_run.input import (
    GetTableMaintenanceRunUseCaseInput,
)
from application.port.inbound.table_maintenance_run.get_table_maintenance_run.output import (
    GetTableMaintenanceRunUseCaseOutput,
)
from base.use_case import UseCase


class GetTableMaintenanceRunUseCase(
    UseCase[GetTableMaintenanceRunUseCaseInput, GetTableMaintenanceRunUseCaseOutput]
):
    """Get one maintenance run."""

    @abstractmethod
    def execute(
        self, request: GetTableMaintenanceRunUseCaseInput
    ) -> GetTableMaintenanceRunUseCaseOutput:
        """Get one maintenance run."""
