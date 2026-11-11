"""Define the table_maintenance_policy_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicy,
    )


def table_maintenance_policy_output_fields(policy: TableMaintenancePolicy) -> dict[str, Any]:
    """Return the primitive fields shared by every table maintenance policy output."""
    return {
        "name": policy.id.value,
        "content": policy.content.to_primitives(),
        "version": policy.version,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }
