"""Define the GetMaintenanceJobStatusUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMaintenanceJobStatusUseCaseInput:
    """Carry the request to get the state of one operation attempt job."""

    run_id: str
    operation: str
    attempt: int
