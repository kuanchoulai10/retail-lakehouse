"""Define the table_discovery_rule_from_request function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_rules import (
    GlobList,
    RuleAction,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.port.inbound.table_discovery_rules import (
        ReplaceTableDiscoveryRulesUseCaseInputItem,
    )


def table_discovery_rule_from_request(
    item: ReplaceTableDiscoveryRulesUseCaseInputItem,
    rule_id: str,
    now: datetime,
) -> TableDiscoveryRule:
    """Build a rule from one requested rule under ``rule_id``; an invalid rule raises ValueError."""
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId(rule_id),
        priority=item.priority,
        action=RuleAction(item.action),
        enabled=item.enabled,
        catalogs=GlobList(globs=tuple(item.catalogs)),
        namespaces=GlobList(globs=tuple(item.namespaces)),
        tables=GlobList(globs=tuple(item.tables)),
        now=now,
    )
