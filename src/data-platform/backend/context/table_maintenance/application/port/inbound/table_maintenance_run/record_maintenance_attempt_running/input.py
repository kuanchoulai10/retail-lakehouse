"""Define the RecordMaintenanceAttemptRunningUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class RecordMaintenanceAttemptRunningUseCaseInput(UseCaseInput):
    """Carry the request to record that the coordinator of a run's attempt started running.

    ``operation`` must be the run's own. ``started_running_at`` is when the coordinator process started and
    ``now`` is when it was read.
    """

    run_id: str
    operation: str
    attempt: int
    started_running_at: datetime
    now: datetime
