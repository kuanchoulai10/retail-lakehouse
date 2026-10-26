"""Define the TableMaintenanceAttemptPolicy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from adapter.temporal_contracts.default_attempt_deadline_seconds import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)


@dataclass(frozen=True)
class TableMaintenanceAttemptPolicy:
    """Describe how a maintenance run attempts each planned operation.

    An operation gets ``max_attempts`` attempts, each bounded by
    ``attempt_deadline`` from its submit, with ``backoffs[n - 1]`` slept after a
    failed attempt ``n``. The reconciliation workflow derives from the same policy how
    long a run in flight may take before it is given up.
    """

    max_attempts: int = 3
    backoffs: tuple[timedelta, ...] = field(
        default=(timedelta(seconds=60), timedelta(seconds=120))
    )
    attempt_deadline: timedelta = field(
        default=timedelta(seconds=DEFAULT_ATTEMPT_DEADLINE_SECONDS)
    )

    def backoff_after(self, attempt: int) -> timedelta:
        """Return the sleep after failed attempt ``attempt`` (1-based)."""
        return self.backoffs[attempt - 1]

    def operation_worst_case(self) -> timedelta:
        """Return the longest an operation can run: every attempt times out."""
        return self.attempt_deadline * self.max_attempts + sum(
            self.backoffs, timedelta()
        )
