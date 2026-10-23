"""Define the DeleteMaintenanceJobUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteMaintenanceJobUseCaseInput:
    """Carry the request to delete a Spark maintenance job."""

    app_name: str
