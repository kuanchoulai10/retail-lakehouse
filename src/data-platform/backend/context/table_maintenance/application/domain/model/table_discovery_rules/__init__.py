"""Discovery rules domain vocabulary, until the discovery policy replaces it.

The rule id and its error now live with the discovery policy and are re-exported here; the one rule
list is keyed by the default discovery policy's id, so ``dp`` names one id type.
"""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID as GLOBAL_TABLE_DISCOVERY_RULES_ID,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryRuleId,
    UnknownDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.glob_list import (
    GlobList,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.rule_action import (
    RuleAction,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.stale_discovery_rules_version import (
    StaleDiscoveryRulesVersion,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.table_discovery_rule import (
    TableDiscoveryRule,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.table_discovery_rules import (
    TableDiscoveryRules,
)

__all__ = [
    "GLOBAL_TABLE_DISCOVERY_RULES_ID",
    "GlobList",
    "RuleAction",
    "StaleDiscoveryRulesVersion",
    "TableDiscoveryRule",
    "TableDiscoveryRuleId",
    "TableDiscoveryRules",
    "UnknownDiscoveryRuleId",
]
