"""Define the plan_scheduled_maintenance domain service."""

from __future__ import annotations

from datetime import datetime

from context.table_maintenance.application.domain.model.shared import (
    MaintenancePlan,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import Table, TableStatus
from context.table_maintenance.application.domain.service.table.assess_maintenance import (
    DEFAULT_SMALL_MANIFEST_BYTES as DEFAULT_SMALL_MANIFEST_BYTES,
    MANIFEST_TARGET_SIZE_PROPERTY as MANIFEST_TARGET_SIZE_PROPERTY,
    assess_maintenance,
)


def plan_scheduled_maintenance(table: Table, observation: TableObservation, now: datetime) -> MaintenancePlan:
    """Decide which operations are due for a table given its observation."""
    settings = table.settings
    if table.status != TableStatus.ACTIVE or settings is None:
        return MaintenancePlan()
    return assess_maintenance(table, settings, observation, now).plan()
