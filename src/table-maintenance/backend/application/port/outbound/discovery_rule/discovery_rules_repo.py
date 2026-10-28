"""Define the DiscoveryRulesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from base.entity_id import EntityId
from base.repository import Repository

if TYPE_CHECKING:
    from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
        TableMaintenancePresetId,
    )


class DiscoveryRulesRepo(Repository[DiscoveryRule]):
    """Persist and query DiscoveryRule aggregates."""

    @abstractmethod
    def update(self, rule: DiscoveryRule) -> DiscoveryRule:
        """Persist the changed rule and return it."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the rule with the given id."""

    @abstractmethod
    def count_by_preset(self, preset_id: TableMaintenancePresetId) -> int:
        """Return how many rules reference the preset."""
