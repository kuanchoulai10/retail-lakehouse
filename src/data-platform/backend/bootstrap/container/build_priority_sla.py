"""Provide the build_priority_sla function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority

if TYPE_CHECKING:
    from bootstrap.configs import SchedulerSettings


def build_priority_sla(settings: SchedulerSettings) -> dict[MaintenancePriority, timedelta]:
    """Return how long a candidate of each priority may wait for a run before it is overdue."""
    sla = settings.sla_seconds
    return {
        MaintenancePriority.P0: timedelta(seconds=sla.p0),
        MaintenancePriority.P1: timedelta(seconds=sla.p1),
        MaintenancePriority.P2: timedelta(seconds=sla.p2),
    }
