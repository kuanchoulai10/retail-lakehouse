"""Define the TableDiscoverySettingsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_discovery_settings import (
    TableDiscoverySettings,
)

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId


class TableDiscoverySettingsRepo(Repository[TableDiscoverySettings]):
    """Persist the singleton TableDiscoverySettings aggregate."""

    @abstractmethod
    def get(self, entity_id: EntityId | ModelEntityId) -> TableDiscoverySettings | None:
        """Return the settings with the given id, or None when absent."""

    @abstractmethod
    def get_settings(self) -> TableDiscoverySettings:
        """Return the singleton settings, enabled by default when absent."""

    @abstractmethod
    def save(self, settings: TableDiscoverySettings) -> None:
        """Insert or replace the singleton settings."""
