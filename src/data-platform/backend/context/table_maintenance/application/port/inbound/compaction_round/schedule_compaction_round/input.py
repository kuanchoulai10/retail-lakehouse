"""Define the ScheduleCompactionRoundUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class ScheduleCompactionRoundUseCaseInput(UseCaseInput):
    """Carry one compaction round's id and the time it runs at.

    The caller names the round, so a retried round keeps its id and is not
    planned twice.
    """

    round_id: str
    now: datetime
