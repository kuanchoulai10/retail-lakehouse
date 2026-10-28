"""Define the InMemoryDiscoveryRulesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.discovery_rule.discovery_rules_repo import (
    DiscoveryRulesRepo,
)

if TYPE_CHECKING:
    from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
    from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
        TableMaintenancePresetId,
    )
    from base.entity_id import EntityId


class InMemoryDiscoveryRulesRepo(DiscoveryRulesRepo):
    """Keep rules in a dict."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, DiscoveryRule] = {}

    def create(self, entity: DiscoveryRule) -> DiscoveryRule:
        """Insert a rule."""
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> DiscoveryRule | None:
        """Return the rule or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[DiscoveryRule]:
        """Return rules ordered by priority then id."""
        return sorted(self.items.values(), key=lambda r: (r.priority, r.id.value))

    def update(self, rule: DiscoveryRule) -> DiscoveryRule:
        """Replace a stored rule."""
        if rule.id.value not in self.items:
            raise LookupError(f"discovery rule {rule.id.value} does not exist")
        self.items[rule.id.value] = rule
        return rule

    def delete(self, entity_id: EntityId) -> None:
        """Remove a rule if present."""
        self.items.pop(entity_id.value, None)

    def count_by_preset(self, preset_id: TableMaintenancePresetId) -> int:
        """Count the rules that reference the preset."""
        return sum(1 for r in self.items.values() if r.preset_id == preset_id)
