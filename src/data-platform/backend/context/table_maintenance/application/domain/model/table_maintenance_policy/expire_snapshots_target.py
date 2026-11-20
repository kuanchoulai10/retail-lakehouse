"""Define the ExpireSnapshotsTarget value object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field, PositiveInt, field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import (
    MAX_AGE,
    MAX_SNAPSHOTS_TO_KEEP,
    PositiveDuration,
)

if TYPE_CHECKING:
    from datetime import timedelta


class ExpireSnapshotsTarget(ValueObject):
    """The retention target; a value left out falls back to the table property, then Iceberg's default.

    The count is at most a Java ``int`` (Iceberg's ``retain_last``) and the age at most 100 years.
    """

    min_snapshots_to_keep: PositiveInt | None = Field(default=None, le=MAX_SNAPSHOTS_TO_KEEP)
    max_snapshot_age: PositiveDuration | None = Field(
        default=None,
        validation_alias="max_snapshot_age_seconds",
        serialization_alias="max_snapshot_age_seconds",
    )

    @field_validator("max_snapshot_age")
    @classmethod
    def _at_most_max_age(cls, value: timedelta | None) -> timedelta | None:
        """Reject an age whose cutoff ``now - age`` would fall before any date."""
        if value is not None and value > MAX_AGE:
            raise ValueError("must be at most 100 years")
        return value
