"""Define the ExpireSnapshotsSettings value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from application.domain.model.shared.invalid_maintenance_settings import (
    InvalidMaintenanceSettings,
)
from base.value_object import ValueObject


@dataclass(frozen=True)
class ExpireSnapshotsSettings(ValueObject):
    """Configure expiry of old snapshots."""

    enabled: bool = True
    min_interval: timedelta = field(default_factory=lambda: timedelta(hours=6))
    older_than: timedelta = field(default_factory=lambda: timedelta(days=1))
    retain_last: int = 10

    def __post_init__(self) -> None:
        """Reject non-positive durations and counts."""
        if self.min_interval <= timedelta(0):
            raise InvalidMaintenanceSettings("min_interval must be positive")
        if self.older_than <= timedelta(0):
            raise InvalidMaintenanceSettings("older_than must be positive")
        if self.retain_last <= 0:
            raise InvalidMaintenanceSettings("retain_last must be positive")
