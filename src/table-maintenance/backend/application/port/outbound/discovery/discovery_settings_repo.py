"""Define the DiscoverySettingsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from application.domain.model.discovery.discovery_settings import DiscoverySettings
from base.repository import Repository


class DiscoverySettingsRepo(Repository[DiscoverySettings]):
    """Persist the singleton DiscoverySettings aggregate."""

    @abstractmethod
    def get_settings(self) -> DiscoverySettings:
        """Return the singleton settings, enabled by default when absent."""

    @abstractmethod
    def save(self, settings: DiscoverySettings) -> None:
        """Insert or replace the singleton settings."""
