"""Test the scheduler settings route."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.compaction_round import (
    GetSchedulerSettingsUseCaseInput,
    GetSchedulerSettingsUseCaseOutput,
    GetSchedulerSettingsUseCaseOutputPriority,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import StubUseCase, build_client


def test_serves_the_scheduler_settings():
    """The route answers how often rounds run, their budget and lease, and each priority's weight and SLA."""
    stub = StubUseCase(
        GetSchedulerSettingsUseCaseOutput(
            round_seconds=120,
            budget_gb_hours=0.05,
            grant_lease_seconds=600,
            priorities=[GetSchedulerSettingsUseCaseOutputPriority(priority="P0", weight=4.0, sla_seconds=3600)],
        )
    )

    response = build_client(get_scheduler_settings=stub).get("/v1/scheduler-settings")

    assert response.status_code == 200
    assert response.json() == {
        "round_seconds": 120,
        "budget_gb_hours": 0.05,
        "grant_lease_seconds": 600,
        "priorities": [{"priority": "P0", "weight": 4.0, "sla_seconds": 3600}],
    }
    assert stub.requests == [GetSchedulerSettingsUseCaseInput()]
