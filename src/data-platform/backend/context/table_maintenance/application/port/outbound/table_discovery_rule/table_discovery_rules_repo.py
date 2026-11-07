"""Define the TableDiscoveryRulesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import EntityId, Repository
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRule,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_preset import (
        TableMaintenancePresetId,
    )


class TableDiscoveryRulesRepo(Repository[TableDiscoveryRule]):
    """Persist and query TableDiscoveryRule aggregates."""

    @abstractmethod
    def update(self, rule: TableDiscoveryRule) -> TableDiscoveryRule:
        """Persist the changed rule and return it."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the rule with the given id."""

    @abstractmethod
    def count_by_preset(self, preset_id: TableMaintenancePresetId) -> int:
        """Return how many rules reference the preset."""
