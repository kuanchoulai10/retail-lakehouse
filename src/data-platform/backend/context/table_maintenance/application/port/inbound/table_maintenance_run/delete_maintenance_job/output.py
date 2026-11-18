"""Define the DeleteMaintenanceJobUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class DeleteMaintenanceJobUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to delete a Spark maintenance job."""

    run_id: str
    operation: str
    attempt: int
