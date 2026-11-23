"""Define the IssueTableMaintenanceRunIdsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.issue_table_maintenance_run_ids.input import (  # noqa: E501
    IssueTableMaintenanceRunIdsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.issue_table_maintenance_run_ids.output import (  # noqa: E501
    IssueTableMaintenanceRunIdsUseCaseOutput,
)


class IssueTableMaintenanceRunIdsUseCase(
    UseCase[IssueTableMaintenanceRunIdsUseCaseInput, IssueTableMaintenanceRunIdsUseCaseOutput]
):
    """Issue the ids of the runs a new plan creates."""

    @abstractmethod
    def execute(self, request: IssueTableMaintenanceRunIdsUseCaseInput) -> IssueTableMaintenanceRunIdsUseCaseOutput:
        """Issue the ids of the runs a new plan creates."""
