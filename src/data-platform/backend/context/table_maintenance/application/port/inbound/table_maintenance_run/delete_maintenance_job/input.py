"""Define the DeleteMaintenanceJobUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteMaintenanceJobUseCaseInput(UseCaseInput):
    """Carry the request to delete the Spark job of one operation attempt."""

    run_id: str
    operation: str
    attempt: int
