"""Define the ExpireSnapshotsExecutionPolicy value object."""

from __future__ import annotations

from pydantic import Field, PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import PositiveDuration


class ExpireSnapshotsExecutionPolicy(ValueObject):
    """Configure how old snapshots are expired."""

    older_than: PositiveDuration = Field(
        validation_alias="older_than_seconds",
        serialization_alias="older_than_seconds",
    )
    retain_last: PositiveInt
