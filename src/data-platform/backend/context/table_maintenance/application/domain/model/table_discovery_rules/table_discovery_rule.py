"""Define the TableDiscoveryRule entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from base import Entity
from context.table_maintenance.application.domain.model.table_discovery_rules.glob_list import (
    GlobList,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.rule_action import (
    RuleAction,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName


class TableDiscoveryRule(Entity[TableDiscoveryRuleId]):
    """One include or exclude rule of the discovery rules, matching tables by globs."""

    id: TableDiscoveryRuleId
    priority: int
    action: RuleAction
    enabled: bool
    catalogs: GlobList
    namespaces: GlobList
    tables: GlobList
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        *,
        id: TableDiscoveryRuleId,  # noqa: A002
        priority: int,
        action: RuleAction,
        enabled: bool,
        catalogs: GlobList,
        namespaces: GlobList,
        tables: GlobList,
        now: datetime,
    ) -> TableDiscoveryRule:
        """Create a rule created and updated at now."""
        return cls(
            id=id,
            priority=priority,
            action=action,
            enabled=enabled,
            catalogs=catalogs,
            namespaces=namespaces,
            tables=tables,
            created_at=now,
            updated_at=now,
        )

    def matches(self, name: TableName) -> bool:
        """Return whether any glob of each field matches and all three fields match."""
        return (
            self.catalogs.matches(name.catalog)
            and self.namespaces.matches(name.namespace)
            and self.tables.matches(name.table)
        )

    def same_definition(self, other: TableDiscoveryRule) -> bool:
        """Return whether both rules say the same, timestamps aside."""
        return _definition(self) == _definition(other)


def _definition(rule: TableDiscoveryRule) -> tuple[object, ...]:
    return (rule.priority, rule.action, rule.enabled, rule.catalogs, rule.namespaces, rule.tables)
