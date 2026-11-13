"""Define the OperationState value object."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar

from base import ValueObject, validated_copy
from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table.attention_mark import (
    AttentionMark,
)
from context.table_maintenance.application.domain.model.table.default_failure_backoff_cap import (
    DEFAULT_FAILURE_BACKOFF_CAP,
)
from context.table_maintenance.application.domain.model.table.recorded_attempt import (
    RecordedAttempt,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table.applied_policy_ref import (
        AppliedPolicyRef,
    )


class OperationState(ValueObject):
    """Track the last attempt, failure streak, remembered size and attention mark of one maintenance operation.

    ``low_use_successes`` counts the successes in a row at the remembered size whose measured use
    would have fit the next smaller size; at ``LOW_USE_RUNS`` the remembered size steps down one size.
    ``last_recorded`` is the attempt whose result was taken in last, so the same result is never
    counted twice.
    """

    LOW_USE_RUNS: ClassVar[int] = 3

    last_attempt_at: datetime | None = None
    consecutive_failures: int = 0
    last_successful_size: ComputeSize | None = None
    attention: AttentionMark | None = None
    low_use_successes: int = 0
    last_recorded: RecordedAttempt | None = None

    def effective_cooldown(self, base: timedelta, cap: timedelta = DEFAULT_FAILURE_BACKOFF_CAP) -> timedelta:
        """Return ``base`` doubled per consecutive failure, capped, never below base."""
        return max(base, min(base * 2**self.consecutive_failures, cap))

    def start_size(self) -> ComputeSize:
        """Return the size the next run starts at: the last successful one, else S."""
        return self.last_successful_size or ComputeSize.S

    def after_success(
        self, at: datetime, size: ComputeSize | None = None, *, fits_smaller: bool = False
    ) -> OperationState:
        """Return the state after a successful attempt, remembering its size when known and lifting attention.

        A success whose measured use would have fit the next smaller size (``fits_smaller``) adds to
        the low-use count when it ran at the remembered size, and starts a new count at another
        size; any other success resets it. The ``LOW_USE_RUNS``-th such success in a row steps the
        remembered size down one (never below S) and resets the count.
        """
        ran_at = size or self.last_successful_size
        low_use = fits_smaller
        same_size = ran_at == self.last_successful_size
        streak = (self.low_use_successes + 1 if same_size else 1) if low_use else 0
        remembered = ran_at
        if streak >= self.LOW_USE_RUNS:
            remembered = (ran_at.smaller() if ran_at else None) or ran_at
            streak = 0
        return validated_copy(
            self,
            last_attempt_at=at,
            consecutive_failures=0,
            last_successful_size=remembered,
            attention=None,
            low_use_successes=streak,
        )

    def recorded(self, attempt: RecordedAttempt) -> OperationState:
        """Return the state remembering that ``attempt``'s result was taken in."""
        return validated_copy(self, last_recorded=attempt)

    def after_failure(self, at: datetime) -> OperationState:
        """Return the state after a failed attempt."""
        return validated_copy(
            self,
            last_attempt_at=at,
            consecutive_failures=self.consecutive_failures + 1,
        )

    def with_attention(self, mark: AttentionMark) -> OperationState:
        """Return the state marked as needing attention."""
        return validated_copy(self, attention=mark)

    def without_attention(self) -> OperationState:
        """Return the state with no attention mark."""
        return validated_copy(self, attention=None)

    def needs_attention_under(self, policy: AppliedPolicyRef) -> bool:
        """Return whether the operation was marked as needing attention under ``policy``.

        A mark holds only under the applicable policy it was set under; once another policy (or
        another version, or the same policy attached elsewhere) applies, the next plan lifts it.
        """
        return self.attention is not None and self.attention.policy == policy
