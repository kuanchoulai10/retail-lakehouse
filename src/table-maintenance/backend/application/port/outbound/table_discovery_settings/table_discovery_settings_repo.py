"""Define the TableDiscoverySettingsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from application.domain.model.table_discovery_settings.table_discovery_settings import (
    TableDiscoverySettings,
)
from base.repository import Repository


class TableDiscoverySettingsRepo(Repository[TableDiscoverySettings]):
    """Persist the singleton TableDiscoverySettings aggregate."""

    @abstractmethod
    def get_settings(self) -> TableDiscoverySettings:
        """Return the singleton settings, enabled by default when absent."""

    @abstractmethod
    def save(self, settings: TableDiscoverySettings) -> None:
        """Insert or replace the singleton settings."""
