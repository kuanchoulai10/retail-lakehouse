"""Define the SkipTableMaintenanceRunUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.skip_table_maintenance_run.input import (  # noqa: E501
    SkipTableMaintenanceRunUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.skip_table_maintenance_run.output import (  # noqa: E501
    SkipTableMaintenanceRunUseCaseOutput,
)


class SkipTableMaintenanceRunUseCase(
    UseCase[SkipTableMaintenanceRunUseCaseInput, SkipTableMaintenanceRunUseCaseOutput]
):
    """Skip a maintenance run that never started, saying why."""

    @abstractmethod
    def execute(self, request: SkipTableMaintenanceRunUseCaseInput) -> SkipTableMaintenanceRunUseCaseOutput:
        """Skip a maintenance run that never started, saying why."""
