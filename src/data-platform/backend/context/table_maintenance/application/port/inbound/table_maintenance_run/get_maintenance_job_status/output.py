"""Define the GetMaintenanceJobStatusUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMaintenanceJobStatusUseCaseOutput:
    """Carry the result of the request to get the state of a Spark maintenance job."""

    state: str
    error: str | None
