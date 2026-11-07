"""Define the plan_manual_maintenance domain service."""

from __future__ import annotations

from collections.abc import Sequence

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenancePlan,
    PlannedOperation,
)


def plan_manual_maintenance(
    operations: Sequence[MaintenanceOperation],
) -> MaintenancePlan:
    """Plan every named operation on the whole table, de-duplicated, in order."""
    requested = set(operations)
    return MaintenancePlan(
        tuple(
            PlannedOperation(op)
            for op in MaintenanceOperation.ordered()
            if op in requested
        )
    )
