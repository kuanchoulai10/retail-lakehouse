"""Define the RemoveOrphanFilesSettings value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from application.domain.model.maintenance_settings.invalid_maintenance_settings import (
    InvalidMaintenanceSettings,
)
from base.value_object import ValueObject

MIN_OLDER_THAN = timedelta(days=1)


@dataclass(frozen=True)
class RemoveOrphanFilesSettings(ValueObject):
    """Configure removal of orphan files; ``older_than`` must be at least 1 day."""

    enabled: bool = True
    min_interval: timedelta = field(default_factory=lambda: timedelta(days=7))
    older_than: timedelta = field(default_factory=lambda: timedelta(days=3))

    def __post_init__(self) -> None:
        """Reject non-positive intervals and an unsafe ``older_than``."""
        if self.min_interval <= timedelta(0):
            raise InvalidMaintenanceSettings("min_interval must be positive")
        if self.older_than < MIN_OLDER_THAN:
            raise InvalidMaintenanceSettings("older_than must be at least 1 day")
