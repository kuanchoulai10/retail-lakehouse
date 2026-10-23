"""Define the DeleteMaintenanceJobUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteMaintenanceJobUseCaseInput:
    """Carry the request to delete the Spark job of one operation attempt."""

    run_id: str
    operation: str
    attempt: int
