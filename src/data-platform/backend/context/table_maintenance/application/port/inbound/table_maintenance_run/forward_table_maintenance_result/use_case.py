"""Define the ForwardTableMaintenanceResultUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.forward_table_maintenance_result.input import (  # noqa: E501
    ForwardTableMaintenanceResultUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.forward_table_maintenance_result.output import (  # noqa: E501
    ForwardTableMaintenanceResultUseCaseOutput,
)


class ForwardTableMaintenanceResultUseCase(
    UseCase[
        ForwardTableMaintenanceResultUseCaseInput,
        ForwardTableMaintenanceResultUseCaseOutput,
    ]
):
    """Forward the result a maintenance job reports to the workflow."""

    @abstractmethod
    def execute(self, request: ForwardTableMaintenanceResultUseCaseInput) -> ForwardTableMaintenanceResultUseCaseOutput:
        """Forward the result a maintenance job reports to the workflow."""
