"""Define the DiscoverySettings aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.domain.model.discovery.discovery_settings_id import (
    DiscoverySettingsId,
)
from base.aggregate_root import AggregateRoot

GLOBAL_ID = DiscoverySettingsId("global")


@dataclass(eq=False)
class DiscoverySettings(AggregateRoot[DiscoverySettingsId]):
    """The singleton switch that turns table discovery on or off."""

    id: DiscoverySettingsId
    enabled: bool
    updated_at: datetime

    @classmethod
    def create(cls, now: datetime, enabled: bool = True) -> DiscoverySettings:
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
