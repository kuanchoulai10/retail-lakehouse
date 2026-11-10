"""Define the RemoveOrphanFilesSettings value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, field_validator

from base.model import ValueObject, WholeSeconds
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
)

MIN_OLDER_THAN = timedelta(days=1)


class RemoveOrphanFilesSettings(ValueObject):
    """Configure removal of orphan files; ``older_than`` must be at least 1 day."""

    enabled: bool = True
    min_interval: PositiveDuration = Field(
        default=timedelta(days=7),
        validation_alias="min_interval_seconds",
        serialization_alias="min_interval_seconds",
    )
    older_than: WholeSeconds = Field(
        default=timedelta(days=3),
        validation_alias="older_than_seconds",
        serialization_alias="older_than_seconds",
    )

    @field_validator("older_than")
    @classmethod
    def _at_least_one_day(cls, value: timedelta) -> timedelta:
        """Reject an ``older_than`` that could delete files of a running write."""
        if value < MIN_OLDER_THAN:
            raise ValueError("must be at least 1 day")
        return value
