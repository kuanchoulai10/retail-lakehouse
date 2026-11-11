"""Define the decide_table_management domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableManagementChange,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
)
from context.table_maintenance.application.domain.service.table_discovery_rule import (
    match_table_discovery_rule,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.model.table_discovery_rule import (
        TableDiscoveryRule,
    )


def decide_table_management(table: Table, rules: Sequence[TableDiscoveryRule], now: datetime) -> TableManagementChange:
    """Apply the discovery rules to a known table and say what changed.

    The first enabled rule matching the table decides: an include rule manages it
    under that rule, an exclude rule or no match unmanages it. A managed table
    that another include rule now decides stays managed and reports
    ``RULE_CHANGED``. A dropped table raises ``InvalidTableTransition``.
    """
    rule = match_table_discovery_rule(rules, table.name)
    was_managed = table.status == TableStatus.MANAGED
    previous_rule_id = table.matched_rule_id
    if rule is not None and rule.effect == RuleEffect.INCLUDE:
        table.manage(rule.id, now)
    else:
        table.unmanage(now)
    if was_managed == table.is_managed:
        if table.matched_rule_id != previous_rule_id:
            return TableManagementChange.RULE_CHANGED
        return TableManagementChange.UNCHANGED
    return TableManagementChange.MANAGED if table.is_managed else TableManagementChange.UNMANAGED
