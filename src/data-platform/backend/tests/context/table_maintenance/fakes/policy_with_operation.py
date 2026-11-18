"""Define the policy_with_operation helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        MaintenancePolicyContent,
    )


def policy_with_operation(
    content: MaintenancePolicyContent, operation: MaintenanceOperation, **changes: object
) -> MaintenancePolicyContent:
    """Return ``content`` with the given fields of one operation's policy changed."""
    operations = content.operations
    changed = operations.for_operation(operation).with_changes(**changes)
    return content.with_changes(operations=operations.with_changes(**{operation.value: changed}))
