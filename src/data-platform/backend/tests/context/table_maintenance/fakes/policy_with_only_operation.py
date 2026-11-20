"""Define the policy_with_only_operation helper."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
)
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation


def policy_with_only_operation(
    operation: MaintenanceOperation, content: MaintenancePolicyContent | None = None
) -> MaintenancePolicyContent:
    """Return ``content`` (the platform default by default) with the blocks of every other operation removed."""
    result = content or MaintenancePolicyContent.platform_default()
    for other in MaintenanceOperation.ordered():
        if other != operation:
            result = policy_with_operation(result, other, None)
    return result
