"""Define the GetMaintenanceJobStatusUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMaintenanceJobStatusUseCaseInput:
    """Carry the request to get the state of a Spark maintenance job."""

    app_name: str
