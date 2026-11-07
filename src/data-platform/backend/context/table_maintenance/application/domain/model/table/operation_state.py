"""Define the OperationState value object."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from base import ValueObject


@dataclass(frozen=True)
class OperationState(ValueObject):
    """Track the last attempt and failure streak of one maintenance operation."""

    last_attempt_at: datetime | None = None
    consecutive_failures: int = 0

    def effective_cooldown(self, base: timedelta, cap: timedelta = timedelta(hours=24)) -> timedelta:
        """Return ``base`` doubled per consecutive failure, capped, never below base."""
        return max(base, min(base * 2**self.consecutive_failures, cap))

    def after_success(self, at: datetime) -> OperationState:
        """Return the state after a successful attempt."""
        return replace(self, last_attempt_at=at, consecutive_failures=0)

    def after_failure(self, at: datetime) -> OperationState:
        """Return the state after a failed attempt."""
        return replace(
            self,
            last_attempt_at=at,
            consecutive_failures=self.consecutive_failures + 1,
        )
