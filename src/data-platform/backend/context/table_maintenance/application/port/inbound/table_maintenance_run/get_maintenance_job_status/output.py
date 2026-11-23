"""Define the GetMaintenanceJobStatusUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetMaintenanceJobStatusUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to get the state of a Spark maintenance job.

    ``started_running_at`` is when the job's coordinator process started, None while it has not or
    when the job is gone or its processes cannot be read.
    """

    state: str
    error: str | None
    started_running_at: datetime | None = None
