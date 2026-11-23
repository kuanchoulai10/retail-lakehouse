"""Define the GetMaintenanceJobProcessesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetMaintenanceJobProcessesUseCaseInput(UseCaseInput):
    """Carry the request to get the live processes of one operation attempt job."""

    run_id: str
    operation: str
    attempt: int
