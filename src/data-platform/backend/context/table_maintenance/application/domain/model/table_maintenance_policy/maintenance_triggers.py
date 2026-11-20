"""Define the MaintenanceTriggers value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.catalog_commit_trigger import (
    CatalogCommitTrigger,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.schedule_trigger import (
    ScheduleTrigger,
)


class MaintenanceTriggers(ValueObject):
    """When a table is checked besides a manual run, a policy change and the table becoming managed.

    The schedule is required. Leaving ``catalog_commit`` out means commits do not trigger a check.
    """

    schedule: ScheduleTrigger
    catalog_commit: CatalogCommitTrigger | None = None
