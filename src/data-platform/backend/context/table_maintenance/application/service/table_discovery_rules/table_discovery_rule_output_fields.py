"""Define the table_discovery_rule_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_discovery_rules import (
        TableDiscoveryRule,
    )


def table_discovery_rule_output_fields(rule: TableDiscoveryRule) -> dict[str, Any]:
    """Return the primitive fields shared by every discovery rule output."""
    return {
        "id": rule.id.value,
        "priority": rule.priority,
        "action": rule.action.value,
        "enabled": rule.enabled,
        "catalogs": list(rule.catalogs.globs),
        "namespaces": list(rule.namespaces.globs),
        "tables": list(rule.tables.globs),
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }
