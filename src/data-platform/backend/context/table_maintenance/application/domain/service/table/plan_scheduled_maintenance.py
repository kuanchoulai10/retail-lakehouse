"""Define the plan_scheduled_maintenance domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenancePlan,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import Table, TableStatus
from context.table_maintenance.application.domain.service.table.assess_maintenance import (
    assess_maintenance,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        MaintenancePolicyContent,
    )


def plan_scheduled_maintenance(
    table: Table, policy: MaintenancePolicyContent, observation: TableObservation, now: datetime
) -> MaintenancePlan:
    """Decide which operations are due for a managed table under its applicable policy."""
    if table.status != TableStatus.MANAGED:
        return MaintenancePlan()
    return assess_maintenance(table, policy, observation, now).plan()
