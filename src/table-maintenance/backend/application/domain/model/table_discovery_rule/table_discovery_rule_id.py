"""Define the TableDiscoveryRuleId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base import EntityId


@dataclass(frozen=True)
class TableDiscoveryRuleId(EntityId):
    """Identify a TableDiscoveryRule."""
