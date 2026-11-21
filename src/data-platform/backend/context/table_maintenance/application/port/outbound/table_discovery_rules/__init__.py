"""Outbound ports for the table_discovery_rules group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    GLOBAL_TABLE_DISCOVERY_RULES_ID,
    GlobList,
    RuleAction,
    StaleDiscoveryRulesVersion,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TableDiscoveryRules,
)
from context.table_maintenance.application.port.outbound.table_discovery_rules.table_discovery_rules_repo import (
    TableDiscoveryRulesRepo,
)

__all__ = [
    "GLOBAL_TABLE_DISCOVERY_RULES_ID",
    "GlobList",
    "RuleAction",
    "StaleDiscoveryRulesVersion",
    "TableDiscoveryPolicyId",
    "TableDiscoveryRule",
    "TableDiscoveryRuleId",
    "TableDiscoveryRules",
    "TableDiscoveryRulesRepo",
]
