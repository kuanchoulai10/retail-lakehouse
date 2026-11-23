"""Define the IssueTableMaintenanceRunIdsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class IssueTableMaintenanceRunIdsUseCaseInput(UseCaseInput):
    """Carry how many run ids to issue, one per planned operation."""

    count: int
