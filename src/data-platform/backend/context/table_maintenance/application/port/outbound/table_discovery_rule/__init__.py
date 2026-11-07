"""Outbound ports for the table_discovery_rule group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.port.outbound.table_discovery_rule.table_discovery_rules_repo import (
    TableDiscoveryRulesRepo,
)

__all__ = [
    "RuleEffect",
    "TablePattern",
    "TableDiscoveryRuleId",
    "TableDiscoveryRule",
    "TableDiscoveryRulesRepo",
    "TableMaintenancePresetId",
]
