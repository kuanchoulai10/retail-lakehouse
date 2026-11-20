"""Define the ExpireSnapshotsTarget value object."""

from __future__ import annotations

from pydantic import Field, PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import PositiveDuration


class ExpireSnapshotsTarget(ValueObject):
    """The retention target; a value left out falls back to the table property, then Iceberg's default."""

    min_snapshots_to_keep: PositiveInt | None = None
    max_snapshot_age: PositiveDuration | None = Field(
        default=None,
        validation_alias="max_snapshot_age_seconds",
        serialization_alias="max_snapshot_age_seconds",
    )
