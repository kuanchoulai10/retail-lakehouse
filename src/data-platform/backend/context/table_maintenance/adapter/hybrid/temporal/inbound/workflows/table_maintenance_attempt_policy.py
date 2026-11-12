"""Define the TableMaintenanceAttemptPolicy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_fencing_policy import (
    TableMaintenanceFencingPolicy,
)


@dataclass(frozen=True)
class TableMaintenanceAttemptPolicy:
    """Describe how a maintenance run attempts each planned operation.

    An operation gets ``max_attempts`` attempts, each bounded by
    ``attempt_deadline`` from its submit, with ``backoffs[n - 1]`` slept after a
    failed attempt ``n``. A timed-out attempt is fenced by ``fencing`` before the
    next one starts. The reconciliation workflow derives from the same policy how
    long a run in flight may take before it is given up.
    """

    max_attempts: int = 3
    backoffs: tuple[timedelta, ...] = field(default=(timedelta(seconds=60), timedelta(seconds=120)))
    attempt_deadline: timedelta = field(default=timedelta(seconds=DEFAULT_ATTEMPT_DEADLINE_SECONDS))
    fencing: TableMaintenanceFencingPolicy = field(default_factory=TableMaintenanceFencingPolicy)

    def backoff_after(self, attempt: int) -> timedelta:
        """Return the sleep after failed attempt ``attempt`` (1-based)."""
        return self.backoffs[attempt - 1]

    def operation_worst_case(self) -> timedelta:
        """Return the longest an operation can run: every attempt times out and is fenced to its bound.

        Pods that outlive the fencing bound keep the operation waiting beyond this;
        the reconciliation workflow gives such a run up after this worst case.
        """
        per_attempt = self.attempt_deadline + self.fencing.confirm_bound
        return per_attempt * self.max_attempts + sum(self.backoffs, timedelta())
