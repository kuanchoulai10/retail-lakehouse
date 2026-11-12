"""Define the OperationState value object."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from base import ValueObject, validated_copy
from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table.attention_mark import (
    AttentionMark,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table.applied_policy_ref import (
        AppliedPolicyRef,
    )


class OperationState(ValueObject):
    """Track the last attempt, failure streak, remembered size and attention mark of one maintenance operation."""

    last_attempt_at: datetime | None = None
    consecutive_failures: int = 0
    last_successful_size: ComputeSize | None = None
    attention: AttentionMark | None = None

    def effective_cooldown(self, base: timedelta, cap: timedelta = timedelta(hours=24)) -> timedelta:
        """Return ``base`` doubled per consecutive failure, capped, never below base."""
        return max(base, min(base * 2**self.consecutive_failures, cap))

    def start_size(self) -> ComputeSize:
        """Return the size the next run starts at: the last successful one, else S."""
        return self.last_successful_size or ComputeSize.S

    def after_success(self, at: datetime, size: ComputeSize | None = None) -> OperationState:
        """Return the state after a successful attempt, remembering its size when known and lifting attention."""
        return validated_copy(
            self,
            last_attempt_at=at,
            consecutive_failures=0,
            last_successful_size=size or self.last_successful_size,
            attention=None,
        )

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
        """Return whether the operation needs attention under ``policy``.

        A mark holds only under the applicable policy it was set under; once another policy (or
        another version, or the same policy attached elsewhere) applies, the operation is tried again.
        """
        return self.attention is not None and self.attention.policy == policy
