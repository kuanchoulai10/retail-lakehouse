"""Define the TableDiscoverySettings aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from context.table_maintenance.application.domain.model.table_discovery_settings.table_discovery_settings_id import (
    TableDiscoverySettingsId,
)
from base import AggregateRoot

GLOBAL_ID = TableDiscoverySettingsId("global")


@dataclass(eq=False)
class TableDiscoverySettings(AggregateRoot[TableDiscoverySettingsId]):
    """The singleton switch that turns table discovery on or off."""

    id: TableDiscoverySettingsId
    enabled: bool
    updated_at: datetime

    @classmethod
    def create(cls, now: datetime, enabled: bool = True) -> TableDiscoverySettings:
        """Create the singleton with id ``global``."""
        return cls(id=GLOBAL_ID, enabled=enabled, updated_at=now)

    def enable(self, now: datetime) -> None:
        """Turn discovery on."""
        self.enabled = True
        self.updated_at = now

    def disable(self, now: datetime) -> None:
        """Turn discovery off."""
        self.enabled = False
        self.updated_at = now
