"""Define the GetMaintenanceJobStatusUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetMaintenanceJobStatusUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to get the state of a Spark maintenance job.

    ``driver_started_at`` is when the job's driver container started, None while it has not or
    when the job is gone or its pods cannot be read.
    """

    state: str
    error: str | None
    driver_started_at: datetime | None = None
