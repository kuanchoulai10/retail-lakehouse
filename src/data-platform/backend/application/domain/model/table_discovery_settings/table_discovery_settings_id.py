"""Define the TableDiscoverySettingsId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base import EntityId


@dataclass(frozen=True)
class TableDiscoverySettingsId(EntityId):
    """Identify the singleton TableDiscoverySettings."""
