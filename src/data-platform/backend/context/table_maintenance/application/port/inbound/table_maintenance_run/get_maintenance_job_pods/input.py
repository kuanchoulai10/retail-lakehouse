"""Define the GetMaintenanceJobPodsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMaintenanceJobPodsUseCaseInput:
    """Carry the request to get the live pods of one operation attempt job."""

    run_id: str
    operation: str
    attempt: int
