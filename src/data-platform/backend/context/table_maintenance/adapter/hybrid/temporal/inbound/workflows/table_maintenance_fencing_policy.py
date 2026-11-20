"""Define the TableMaintenanceFencingPolicy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta


@dataclass(frozen=True)
class TableMaintenanceFencingPolicy:
    """Describe how an ended attempt is fenced before the next one is submitted.

    After deleting the attempt's Spark job, the workflow polls the attempt's live
    pods every ``poll_interval``. Pods still live ``confirm_bound`` after the
    delete fail the operation; the workflow then polls every
    ``slow_poll_interval`` until they are gone.
    """

    poll_interval: timedelta = field(default=timedelta(seconds=30))
    confirm_bound: timedelta = field(default=timedelta(minutes=15))
    slow_poll_interval: timedelta = field(default=timedelta(minutes=5))
