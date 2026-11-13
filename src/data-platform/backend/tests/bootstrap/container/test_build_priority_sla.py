"""Test the per-priority SLA built from the scheduler settings."""

from __future__ import annotations

from datetime import timedelta

from bootstrap.configs import PrioritySlaSettings, SchedulerSettings
from bootstrap.container import build_priority_sla
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority


def test_default_settings_give_the_default_sla():
    """Without settings P0 waits an hour, P1 four hours and P2 eight hours before it is overdue."""
    assert build_priority_sla(SchedulerSettings()) == {
        MaintenancePriority.P0: timedelta(hours=1),
        MaintenancePriority.P1: timedelta(hours=4),
        MaintenancePriority.P2: timedelta(hours=8),
    }


def test_every_sla_reaches_its_priority():
    """Each priority's SLA is its setting in seconds."""
    settings = SchedulerSettings(sla_seconds=PrioritySlaSettings(p0=60, p1=120, p2=180))

    assert build_priority_sla(settings) == {
        MaintenancePriority.P0: timedelta(seconds=60),
        MaintenancePriority.P1: timedelta(seconds=120),
        MaintenancePriority.P2: timedelta(seconds=180),
    }
