"""Define the RemoveOrphanFilesTarget value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MAX_AGE, WholeSeconds

MIN_OLDER_THAN = timedelta(days=1)


class RemoveOrphanFilesTarget(ValueObject):
    """The orphan file target; ``older_than`` must be at least 1 day and at most 100 years."""

    older_than: WholeSeconds = Field(
        validation_alias="older_than_seconds",
        serialization_alias="older_than_seconds",
    )

    @field_validator("older_than")
    @classmethod
    def _between_a_day_and_max_age(cls, value: timedelta) -> timedelta:
        """Reject an ``older_than`` that could delete files of a running write, or whose cutoff is no date."""
        if value < MIN_OLDER_THAN:
            raise ValueError("must be at least 1 day")
        if value > MAX_AGE:
            raise ValueError("must be at most 100 years")
        return value
