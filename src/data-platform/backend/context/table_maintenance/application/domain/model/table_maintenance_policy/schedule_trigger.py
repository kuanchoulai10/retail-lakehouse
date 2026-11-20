"""Define the ScheduleTrigger value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import WholeSeconds

MIN_EVERY = timedelta(minutes=1)
MAX_EVERY = timedelta(days=7)


class ScheduleTrigger(ValueObject):
    """Check the table at least this often, so a table whose events are lost is still checked."""

    every: WholeSeconds = Field(
        validation_alias="every_seconds",
        serialization_alias="every_seconds",
    )

    @field_validator("every")
    @classmethod
    def _within_bounds(cls, value: timedelta) -> timedelta:
        """Keep the interval between a minute (catalog reads per table) and a week."""
        if not MIN_EVERY <= value <= MAX_EVERY:
            raise ValueError("must be between 60 and 604800 seconds")
        return value
