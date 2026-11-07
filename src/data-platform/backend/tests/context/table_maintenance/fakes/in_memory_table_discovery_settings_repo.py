"""Define the InMemoryTableDiscoverySettingsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_settings import (
    GLOBAL_ID,
    TableDiscoverySettings,
)
from context.table_maintenance.application.port.outbound.table_discovery_settings import (
    TableDiscoverySettingsRepo,
)

if TYPE_CHECKING:
    from datetime import datetime

    from base import EntityId


class InMemoryTableDiscoverySettingsRepo(TableDiscoverySettingsRepo):
    """Hold the singleton settings, enabled by default."""

    def __init__(self, now: datetime) -> None:
        """Start with discovery enabled."""
        self.settings = TableDiscoverySettings.create(now)

    def create(self, entity: TableDiscoverySettings) -> TableDiscoverySettings:
        """Store the singleton."""
        self.settings = entity
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoverySettings | None:
        """Return the singleton when the id is ``global``."""
        return self.settings if entity_id == GLOBAL_ID else None

    def list_all(self) -> list[TableDiscoverySettings]:
        """Return the singleton."""
        return [self.settings]

    def get_settings(self) -> TableDiscoverySettings:
        """Return the singleton."""
        return self.settings

    def save(self, settings: TableDiscoverySettings) -> None:
        """Replace the singleton."""
        self.settings = settings
