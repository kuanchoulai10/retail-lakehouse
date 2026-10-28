"""Outbound ports for the table_discovery_rule group."""

from __future__ import annotations

from application.domain.model.table_discovery_rule import (
    TableDiscoveryRule,
    TableDiscoveryRuleId,
)
from application.domain.model.table_maintenance_preset import TableMaintenancePresetId
from application.port.outbound.table_discovery_rule.table_discovery_rules_repo import (
    TableDiscoveryRulesRepo,
)

__all__ = [
    "TableDiscoveryRuleId",
    "TableDiscoveryRule",
    "TableDiscoveryRulesRepo",
    "TableMaintenancePresetId",
]
