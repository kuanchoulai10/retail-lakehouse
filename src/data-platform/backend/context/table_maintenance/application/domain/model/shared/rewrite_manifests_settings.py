"""Define the RewriteManifestsSettings value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from context.table_maintenance.application.domain.model.shared.invalid_maintenance_settings import (
    InvalidMaintenanceSettings,
)
from base import ValueObject


@dataclass(frozen=True)
class RewriteManifestsSettings(ValueObject):
    """Configure rewriting of small manifest files.

    ``small_manifest_bytes`` of None falls back to the table property
    ``commit.manifest.target-size-bytes``, else 8 MiB.
    """

    enabled: bool = True
    min_interval: timedelta = field(default_factory=lambda: timedelta(hours=6))
    min_small_manifests: int = 5
    small_manifest_bytes: int | None = None

    def __post_init__(self) -> None:
        """Reject non-positive intervals and counts."""
        if self.min_interval <= timedelta(0):
            raise InvalidMaintenanceSettings("min_interval must be positive")
        if self.min_small_manifests <= 0:
            raise InvalidMaintenanceSettings("min_small_manifests must be positive")
        if self.small_manifest_bytes is not None and self.small_manifest_bytes <= 0:
            raise InvalidMaintenanceSettings("small_manifest_bytes must be positive")
