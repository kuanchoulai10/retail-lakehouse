"""Define the InMemoryTableDiscoveryRulesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_discovery_rules import (
    StaleDiscoveryRulesVersion,
    TableDiscoveryRules,
    TableDiscoveryRulesRepo,
)

if TYPE_CHECKING:
    from base import EntityId


class InMemoryTableDiscoveryRulesRepo(TableDiscoveryRulesRepo):
    """Keep the one rule list, handing out copies so an unsaved change never leaks in."""

    def __init__(self) -> None:
        """Start with no saved rules."""
        self._stored = TableDiscoveryRules.empty()

    def create(self, entity: TableDiscoveryRules) -> TableDiscoveryRules:
        """Store the list as given."""
        self._stored = _copy(entity)
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoveryRules | None:
        """Return the list when the id is the singleton's."""
        return self.get_rules() if entity_id == self._stored.id else None

    def list_all(self) -> list[TableDiscoveryRules]:
        """Return the one list."""
        return [self.get_rules()]

    def get_rules(self) -> TableDiscoveryRules:
        """Return a copy of the stored list."""
        return _copy(self._stored)

    def save(self, rules: TableDiscoveryRules) -> TableDiscoveryRules:
        """Store the list when it was replaced from the stored version."""
        if self._stored.version != rules.version - 1:
            raise StaleDiscoveryRulesVersion(f"discovery rules were changed concurrently (at {self._stored.version})")
        self._stored = _copy(rules)
        return rules


def _copy(rules: TableDiscoveryRules) -> TableDiscoveryRules:
    return TableDiscoveryRules(id=rules.id, rules=rules.rules, version=rules.version)
