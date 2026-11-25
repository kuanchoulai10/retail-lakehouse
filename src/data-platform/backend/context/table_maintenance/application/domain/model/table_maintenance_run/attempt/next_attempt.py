"""Define the NextAttempt value object."""

from __future__ import annotations

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table_maintenance_run.attempt.next_step import (
    NextStep,
)


class NextAttempt(ValueObject):
    """Decide what follows a maintenance attempt, and at which size when it retries."""

    step: NextStep
    size: ComputeSize | None = None

    @model_validator(mode="after")
    def _size_only_for_a_retry(self) -> NextAttempt:
        """Require a size for a retry and refuse one for a stop."""
        if self.step.retries and self.size is None:
            raise ValueError(f"next step {self.step.value} requires a size")
        if not self.step.retries and self.size is not None:
            raise ValueError(f"next step {self.step.value} takes no size")
        return self
