"""Define the discovery_rule_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule


def discovery_rule_output_fields(rule: DiscoveryRule) -> dict[str, Any]:
    """Return the primitive fields shared by every discovery rule output."""
    return {
        "id": rule.id.value,
        "priority": rule.priority,
        "effect": rule.effect.value,
        "catalog_pattern": rule.pattern.catalog,
        "namespace_pattern": rule.pattern.namespace,
        "table_pattern": rule.pattern.table,
        "template_id": None if rule.template_id is None else rule.template_id.value,
        "enabled": rule.enabled,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }
