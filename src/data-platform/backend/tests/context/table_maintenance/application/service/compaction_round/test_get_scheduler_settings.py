"""Test the GetSchedulerSettingsService."""

from __future__ import annotations

from datetime import timedelta

from context.table_maintenance.application.domain.model.compaction_round import PriorityWeights
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetSchedulerSettingsUseCaseInput,
    GetSchedulerSettingsUseCaseOutput,
)
from context.table_maintenance.application.service.compaction_round import GetSchedulerSettingsService


def test_reports_the_round_settings_and_each_priority_weight_and_sla():
    """The settings a round runs under come back, one entry per priority from P0 to P2."""
    service = GetSchedulerSettingsService(
        weights=PriorityWeights(p0=4.0, p1=2.0, p2=1.0),
        sla={
            MaintenancePriority.P2: timedelta(hours=8),
            MaintenancePriority.P0: timedelta(hours=1),
            MaintenancePriority.P1: timedelta(hours=4),
        },
        round_seconds=120,
        budget_gb_hours=0.05,
        grant_lease=timedelta(minutes=10),
    )

    output = service.execute(GetSchedulerSettingsUseCaseInput())

    assert (output.round_seconds, output.budget_gb_hours, output.grant_lease_seconds) == (120, 0.05, 600)
    assert output.priorities == (
        GetSchedulerSettingsUseCaseOutput.Priority(priority="P0", weight=4.0, sla_seconds=3600),
        GetSchedulerSettingsUseCaseOutput.Priority(priority="P1", weight=2.0, sla_seconds=14400),
        GetSchedulerSettingsUseCaseOutput.Priority(priority="P2", weight=1.0, sla_seconds=28800),
    )
