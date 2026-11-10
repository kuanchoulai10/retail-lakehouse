"""Define the RewriteDataFilesSettings value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field, PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.compaction_scope import (
    CompactionScope,
)
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
)


class RewriteDataFilesSettings(ValueObject):
    """Configure compaction of small data files."""

    enabled: bool = True
    min_interval: PositiveDuration = Field(
        default=timedelta(hours=1),
        validation_alias="min_interval_seconds",
        serialization_alias="min_interval_seconds",
    )
    scope: CompactionScope = CompactionScope.PARTITION
    target_file_size_bytes: PositiveInt | None = None
    min_reducible_files: PositiveInt = 5
