"""Define the discovery_rule_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_discovery_policy import DiscoveryRules


def discovery_rule_fields(rules: DiscoveryRules) -> tuple[dict[str, str], ...]:
    """Return each rule as ``{"action", "table_name_pattern"}``, in order."""
    return tuple(
        {"action": rule.action.value, "table_name_pattern": rule.table_name_pattern.value} for rule in rules.rules
    )
