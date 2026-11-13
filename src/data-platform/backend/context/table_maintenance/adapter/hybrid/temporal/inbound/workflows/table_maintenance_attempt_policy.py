"""Define the TableMaintenanceAttemptPolicy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_fencing_policy import (
    TableMaintenanceFencingPolicy,
)


@dataclass(frozen=True)
class TableMaintenanceAttemptPolicy:
    """Describe how a maintenance run attempts each planned operation.

    An operation gets ``max_attempts`` attempts, each bounded by
    ``attempt_deadline`` from its submit, with ``backoffs[n - 1]`` slept after a
    failed attempt ``n`` (the last backoff again once ``n`` is past the list). A
    timed-out attempt is fenced by ``fencing`` before the next one starts. The
    reconciliation workflow derives from the same policy how long a run in flight
    may take before it is given up.
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    backoffs: tuple[timedelta, ...] = field(default=(timedelta(seconds=60), timedelta(seconds=120)))
    attempt_deadline: timedelta = field(default=timedelta(seconds=DEFAULT_ATTEMPT_DEADLINE_SECONDS))
    fencing: TableMaintenanceFencingPolicy = field(default_factory=TableMaintenanceFencingPolicy)

    def backoff_after(self, attempt: int) -> timedelta:
        """Return the sleep after failed attempt ``attempt`` (1-based)."""
        return self.backoffs[min(attempt, len(self.backoffs)) - 1]

    def total_backoff(self) -> timedelta:
        """Return the sleeps of an operation that fails every attempt: one after each attempt but the last."""
        return sum((self.backoff_after(n) for n in range(1, self.max_attempts)), timedelta())

    def operation_worst_case(self) -> timedelta:
        """Return the longest an operation can run: every attempt times out and is fenced to its bound.

        Pods that outlive the fencing bound keep the operation waiting beyond this;
        the reconciliation workflow gives such a run up after this worst case.
        """
        per_attempt = self.attempt_deadline + self.fencing.confirm_bound
        return per_attempt * self.max_attempts + self.total_backoff()

    def unfenced_operation_worst_case(self) -> timedelta:
        """Return the worst case of an operation whose attempts are not fenced, as before fencing existed.

        A reconciliation history from before fencing gave runs up on this bound, so it replays with it.
        """
        return self.attempt_deadline * self.max_attempts + self.total_backoff()
