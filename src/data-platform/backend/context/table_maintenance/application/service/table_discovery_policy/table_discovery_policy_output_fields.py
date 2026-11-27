"""Define the table_discovery_policy_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.service.table_discovery_policy.discovery_rule_fields import (
    discovery_rule_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        TableDiscoveryPolicy,
    )


def table_discovery_policy_output_fields(policy: TableDiscoveryPolicy) -> dict[str, Any]:
    """Return the primitive fields shared by every discovery policy output."""
    return {
        "id": policy.id.value,
        "name": policy.name.value,
        "description": policy.description,
        "rules": discovery_rule_fields(policy.rules),
        "version": policy.version,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }
