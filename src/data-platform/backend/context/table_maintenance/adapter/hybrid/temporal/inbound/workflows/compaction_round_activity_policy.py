"""Define the CompactionRoundActivityPolicy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio.common import RetryPolicy


@dataclass(frozen=True)
class CompactionRoundActivityPolicy:
    """Describe how a compaction round runs its activities, and the longest they can take.

    The round's scheduling activity gets ``round_timeout`` per attempt, each
    signal to a granted table ``signal_timeout``; both get ``max_attempts``
    attempts, backing off from ``initial_backoff`` by ``backoff_coefficient``.
    The schedule derives the round's execution timeout from ``worst_case``, so
    a round is never ended while an attempt it may still retry could save
    grants that nobody would then signal.
    """

    round_timeout: timedelta = field(default=timedelta(minutes=2))
    signal_timeout: timedelta = field(default=timedelta(seconds=30))
    max_attempts: int = 5
    initial_backoff: timedelta = field(default=timedelta(seconds=2))
    backoff_coefficient: float = 2.0

    def retry_policy(self) -> RetryPolicy:
        """Return the retry policy of every round activity."""
        return RetryPolicy(
            maximum_attempts=self.max_attempts,
            initial_interval=self.initial_backoff,
            backoff_coefficient=self.backoff_coefficient,
        )

    def worst_case(self) -> timedelta:
        """Return the longest a round's activities can take: every attempt of each times out.

        The signals run side by side after the scheduling activity, so one
        signal's worst case adds to the round's.
        """
        return self._retried(self.round_timeout) + self._retried(self.signal_timeout)

    def _retried(self, attempt_timeout: timedelta) -> timedelta:
        backoff = sum(
            (self.initial_backoff * self.backoff_coefficient**n for n in range(self.max_attempts - 1)),
            timedelta(),
        )
        return self.max_attempts * attempt_timeout + backoff
