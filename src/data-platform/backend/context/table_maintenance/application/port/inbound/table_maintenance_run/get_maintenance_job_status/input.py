"""Define the GetMaintenanceJobStatusUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetMaintenanceJobStatusUseCaseInput(UseCaseInput):
    """Carry the request to get the state of one operation attempt job."""

    run_id: str
    operation: str
    attempt: int
