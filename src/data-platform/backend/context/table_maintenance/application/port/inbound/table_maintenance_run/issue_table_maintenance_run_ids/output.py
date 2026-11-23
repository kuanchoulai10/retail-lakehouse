"""Define the IssueTableMaintenanceRunIdsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class IssueTableMaintenanceRunIdsUseCaseOutput(UseCaseOutput):
    """Carry the new run ids, all distinct."""

    run_ids: tuple[str, ...]
