"""Define the DiscoverySettingsId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class DiscoverySettingsId(EntityId):
    """Identify the singleton DiscoverySettings."""
