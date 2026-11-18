"""Define the GetMaintenanceJobStatusUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetMaintenanceJobStatusUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to get the state of a Spark maintenance job."""

    state: str
    error: str | None
