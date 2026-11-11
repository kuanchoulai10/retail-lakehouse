"""Define the TriggerPolicy value object."""

from __future__ import annotations

from pydantic import Field

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import NonNegativeDuration


class TriggerPolicy[C: ValueObject](ValueObject):
    """Decide when an operation is due: a cooldown between runs and its conditions."""

    cooldown: NonNegativeDuration = Field(
        validation_alias="cooldown_seconds",
        serialization_alias="cooldown_seconds",
    )
    conditions: C
