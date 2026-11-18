"""Define the GetMaintenanceJobPodsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetMaintenanceJobPodsUseCaseInput(UseCaseInput):
    """Carry the request to get the live pods of one operation attempt job."""

    run_id: str
    operation: str
    attempt: int
