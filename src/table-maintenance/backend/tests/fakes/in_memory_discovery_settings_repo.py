"""Define the InMemoryDiscoverySettingsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.discovery.discovery_settings import (
    GLOBAL_ID,
    DiscoverySettings,
)
from application.port.outbound.discovery.discovery_settings_repo import (
    DiscoverySettingsRepo,
)

if TYPE_CHECKING:
    from datetime import datetime

    from base.entity_id import EntityId


class InMemoryDiscoverySettingsRepo(DiscoverySettingsRepo):
    """Hold the singleton settings, enabled by default."""

    def __init__(self, now: datetime) -> None:
        """Start with discovery enabled."""
        self.settings = DiscoverySettings.create(now)

    def create(self, entity: DiscoverySettings) -> DiscoverySettings:
        """Store the singleton."""
        self.settings = entity
        return entity

    def get(self, entity_id: EntityId) -> DiscoverySettings | None:
        """Return the singleton when the id is ``global``."""
        return self.settings if entity_id == GLOBAL_ID else None

    def list_all(self) -> list[DiscoverySettings]:
        """Return the singleton."""
        return [self.settings]

    def get_settings(self) -> DiscoverySettings:
        """Return the singleton."""
        return self.settings

    def save(self, settings: DiscoverySettings) -> None:
        """Replace the singleton."""
        self.settings = settings
