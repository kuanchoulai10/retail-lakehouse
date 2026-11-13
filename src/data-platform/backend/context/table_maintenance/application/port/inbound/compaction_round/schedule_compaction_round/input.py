"""Define the ScheduleCompactionRoundUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ScheduleCompactionRoundUseCaseInput:
    """Carry one compaction round's id and the time it runs at.

    The caller names the round, so a retried round keeps its id and is not
    planned twice.
    """

    round_id: str
    now: datetime
