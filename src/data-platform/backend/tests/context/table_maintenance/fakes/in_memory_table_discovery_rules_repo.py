"""Define the InMemoryTableDiscoveryRulesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_discovery_rule import (
    TableDiscoveryRulesRepo,
)

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.table_maintenance.application.domain.model.table_discovery_rule import (
        TableDiscoveryRule,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_preset import (
        TableMaintenancePresetId,
    )


class InMemoryTableDiscoveryRulesRepo(TableDiscoveryRulesRepo):
    """Keep rules in a dict."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableDiscoveryRule] = {}

    def create(self, entity: TableDiscoveryRule) -> TableDiscoveryRule:
        """Insert a rule."""
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId | ModelEntityId) -> TableDiscoveryRule | None:
        """Return the rule or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[TableDiscoveryRule]:
        """Return rules ordered by priority then id."""
        return sorted(self.items.values(), key=lambda r: (r.priority, r.id.value))

    def update(self, rule: TableDiscoveryRule) -> TableDiscoveryRule:
        """Replace a stored rule."""
        if rule.id.value not in self.items:
            raise LookupError(f"discovery rule {rule.id.value} does not exist")
        self.items[rule.id.value] = rule
        return rule

    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Remove a rule if present."""
        self.items.pop(entity_id.value, None)

    def count_by_preset(self, preset_id: TableMaintenancePresetId) -> int:
        """Count the rules that reference the preset."""
        return sum(1 for r in self.items.values() if r.preset_id == preset_id)
