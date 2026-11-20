"""Define the RecordMaintenanceAttemptRunningUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class RecordMaintenanceAttemptRunningUseCaseOutput(UseCaseOutput):
    """Carry the operation's status and the attempt's recorded running time after the request.

    ``started_running_at`` is None when the attempt has no history entry to hold it.
    """

    status: str
    started_running_at: datetime | None
