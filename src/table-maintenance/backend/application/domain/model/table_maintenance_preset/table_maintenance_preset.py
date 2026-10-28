"""Define the TableMaintenancePreset aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from base.aggregate_root import AggregateRoot


@dataclass(eq=False)
class TableMaintenancePreset(AggregateRoot[TableMaintenancePresetId]):
    """A named, reusable set of maintenance settings."""

    id: TableMaintenancePresetId
    name: str
    settings: MaintenanceSettings
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        id: TableMaintenancePresetId,  # noqa: A002
        name: str,
        settings: MaintenanceSettings,
        now: datetime,
    ) -> TableMaintenancePreset:
        """Create a preset."""
        return cls(id=id, name=name, settings=settings, created_at=now, updated_at=now)

    def rename(self, name: str, now: datetime) -> None:
        """Rename the preset."""
        self.name = name
        self.updated_at = now

    def update_settings(self, settings: MaintenanceSettings, now: datetime) -> None:
        """Replace the preset's settings."""
        self.settings = settings
        self.updated_at = now
