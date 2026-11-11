"""Define the decide_table_management domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableManagementChange,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    RuleAction,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.model.table_discovery_rules import (
        TableDiscoveryRules,
    )


def decide_table_management(table: Table, rules: TableDiscoveryRules, now: datetime) -> TableManagementChange:
    """Apply the discovery rules to a known table and say what changed.

    The rule ``rules.decide`` returns decides: an include rule manages the table
    under that rule, an exclude rule or no rule unmanages it. A managed table that
    another include rule now decides stays managed and reports ``RULE_CHANGED``.
    A dropped table raises ``InvalidTableTransition``.
    """
    rule = rules.decide(table.name)
    was_managed = table.status == TableStatus.MANAGED
    previous_rule_id = table.matched_rule_id
    if rule is not None and rule.action == RuleAction.INCLUDE:
        table.manage(rule.id, now)
    else:
        table.unmanage(now)
    if was_managed == table.is_managed:
        if table.matched_rule_id != previous_rule_id:
            return TableManagementChange.RULE_CHANGED
        return TableManagementChange.UNCHANGED
    return TableManagementChange.MANAGED if table.is_managed else TableManagementChange.UNMANAGED
