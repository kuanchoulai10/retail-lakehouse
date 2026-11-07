"""Discovery rule domain vocabulary."""

from __future__ import annotations

from application.domain.model.table_discovery_rule.invalid_table_discovery_rule import (
    InvalidTableDiscoveryRule,
)
from application.domain.model.table_discovery_rule.rule_effect import RuleEffect
from application.domain.model.table_discovery_rule.table_discovery_rule import (
    TableDiscoveryRule,
)
from application.domain.model.table_discovery_rule.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)
from application.domain.model.table_discovery_rule.table_pattern import TablePattern

__all__ = [
    "InvalidTableDiscoveryRule",
    "RuleEffect",
    "TableDiscoveryRule",
    "TableDiscoveryRuleId",
    "TablePattern",
]
