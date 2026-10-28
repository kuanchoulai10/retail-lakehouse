"""Define the RewriteDataFilesSettings value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from application.domain.model.shared.compaction_scope import (
    CompactionScope,
)
from application.domain.model.shared.invalid_maintenance_settings import (
    InvalidMaintenanceSettings,
)
from base.value_object import ValueObject


@dataclass(frozen=True)
class RewriteDataFilesSettings(ValueObject):
    """Configure compaction of small data files."""

    enabled: bool = True
    min_interval: timedelta = field(default_factory=lambda: timedelta(hours=1))
    scope: CompactionScope = CompactionScope.PARTITION
    target_file_size_bytes: int | None = None
    min_reducible_files: int = 5

    def __post_init__(self) -> None:
        """Reject non-positive intervals and counts."""
        if self.min_interval <= timedelta(0):
            raise InvalidMaintenanceSettings("min_interval must be positive")
        if self.target_file_size_bytes is not None and self.target_file_size_bytes <= 0:
            raise InvalidMaintenanceSettings("target_file_size_bytes must be positive")
        if self.min_reducible_files <= 0:
            raise InvalidMaintenanceSettings("min_reducible_files must be positive")
