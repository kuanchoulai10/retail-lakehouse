"""Define the DeleteMaintenanceJobUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteMaintenanceJobUseCaseOutput:
    """Carry the result of the request to delete a Spark maintenance job."""

    run_id: str
    operation: str
    attempt: int
