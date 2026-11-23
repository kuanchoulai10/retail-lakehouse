"""Define the IssueTableMaintenanceRunIdsService."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TableMaintenanceRunId
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    IssueTableMaintenanceRunIdsUseCase,
    IssueTableMaintenanceRunIdsUseCaseInput,
    IssueTableMaintenanceRunIdsUseCaseOutput,
)


class IssueTableMaintenanceRunIdsService(IssueTableMaintenanceRunIdsUseCase):
    """Issue the ids of the runs a new plan creates."""

    def execute(self, request: IssueTableMaintenanceRunIdsUseCaseInput) -> IssueTableMaintenanceRunIdsUseCaseOutput:
        """Return ``count`` fresh ``mr-`` ids; a negative ``count`` raises ``ValidationError``."""
        if request.count < 0:
            raise ValidationError(f"count must be at least 0, got {request.count}")
        return IssueTableMaintenanceRunIdsUseCaseOutput(
            run_ids=tuple(TableMaintenanceRunId.new().value for _ in range(request.count))
        )
