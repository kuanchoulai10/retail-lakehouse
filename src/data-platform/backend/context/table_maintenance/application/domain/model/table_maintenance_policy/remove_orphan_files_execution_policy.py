"""Define the RemoveOrphanFilesExecutionPolicy value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import WholeSeconds

MIN_OLDER_THAN = timedelta(days=1)


class RemoveOrphanFilesExecutionPolicy(ValueObject):
    """Configure how orphan files are removed; ``older_than`` must be at least 1 day."""

    older_than: WholeSeconds = Field(
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
