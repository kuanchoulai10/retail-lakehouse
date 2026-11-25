"""Define the CancelTableMaintenanceRunUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.cancel_table_maintenance_run.input import (  # noqa: E501
    CancelTableMaintenanceRunUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.cancel_table_maintenance_run.output import (  # noqa: E501
    CancelTableMaintenanceRunUseCaseOutput,
)


class CancelTableMaintenanceRunUseCase(
    UseCase[CancelTableMaintenanceRunUseCaseInput, CancelTableMaintenanceRunUseCaseOutput]
):
    """Cancel a maintenance run with no attempt in flight: one pending or waiting to retry."""

    @abstractmethod
    def execute(self, request: CancelTableMaintenanceRunUseCaseInput) -> CancelTableMaintenanceRunUseCaseOutput:
        """Cancel a maintenance run with no attempt in flight: one pending or waiting to retry."""
