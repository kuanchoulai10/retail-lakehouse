"""Define the TableMaintenanceActivityPolicy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio.common import RetryPolicy


@dataclass(frozen=True)
class TableMaintenanceActivityPolicy:
    """Describe how a table maintenance workflow runs each activity, and the longest one can take.

    Every activity gets ``start_to_close`` per attempt and ``max_attempts`` attempts, backing off
    from ``initial_backoff`` by ``backoff_coefficient``. The reconciliation bounds how long it waits
    for a run that reported to close by ``worst_case``: the run's report activity may still be
    retried that long after the report landed.
    """

    start_to_close: timedelta = field(default=timedelta(minutes=2))
    max_attempts: int = 5
    initial_backoff: timedelta = field(default=timedelta(seconds=2))
    backoff_coefficient: float = 2.0

    def retry_policy(self) -> RetryPolicy:
        """Return the retry policy of every maintenance activity."""
        return RetryPolicy(
            maximum_attempts=self.max_attempts,
            initial_interval=self.initial_backoff,
            backoff_coefficient=self.backoff_coefficient,
        )

    def worst_case(self) -> timedelta:
        """Return the longest one activity can take: every attempt times out, with the backoffs between."""
        backoff = sum(
            (self.initial_backoff * self.backoff_coefficient**n for n in range(self.max_attempts - 1)),
            timedelta(),
        )
        return self.max_attempts * self.start_to_close + backoff
