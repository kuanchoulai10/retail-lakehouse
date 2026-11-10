"""Define the ExpireSnapshotsSettings value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, PositiveInt

from base.model import ValueObject
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
)


class ExpireSnapshotsSettings(ValueObject):
    """Configure expiry of old snapshots."""

    enabled: bool = True
    min_interval: PositiveDuration = Field(
        default=timedelta(hours=6),
        validation_alias="min_interval_seconds",
        serialization_alias="min_interval_seconds",
    )
    older_than: PositiveDuration = Field(
        default=timedelta(days=1),
        validation_alias="older_than_seconds",
        serialization_alias="older_than_seconds",
    )
    retain_last: PositiveInt = 10
