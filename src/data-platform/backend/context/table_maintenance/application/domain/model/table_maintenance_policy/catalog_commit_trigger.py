"""Define the CatalogCommitTrigger value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import WholeSeconds

MAX_DEBOUNCE = timedelta(days=1)


class CatalogCommitTrigger(ValueObject):
    """Check the table after catalog commits, once the debounce window opened by the first commit closes."""

    debounce: WholeSeconds = Field(
        default=timedelta(minutes=5),
        validation_alias="debounce_seconds",
        serialization_alias="debounce_seconds",
    )

    @field_validator("debounce")
    @classmethod
    def _within_bounds(cls, value: timedelta) -> timedelta:
        """Keep the debounce between none and a day."""
        if not timedelta(0) <= value <= MAX_DEBOUNCE:
            raise ValueError("must be between 0 and 86400 seconds")
        return value
