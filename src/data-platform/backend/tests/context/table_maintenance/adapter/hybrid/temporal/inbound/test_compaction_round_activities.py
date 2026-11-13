"""Test the CompactionRoundActivities."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    CompactionRoundActivities,
)
from context.table_maintenance.application.port.inbound.compaction_round import (
    ScheduleCompactionRoundUseCase,
    ScheduleCompactionRoundUseCaseInput,
    ScheduleCompactionRoundUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.compaction_candidate import (
    StaleCompactionCandidate,
)

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


class FakeSchedule(ScheduleCompactionRoundUseCase):
    """Record each round request and answer a fixed round, or raise."""

    def __init__(self, error: Exception | None = None) -> None:
        """Start with no requests."""
        self.requests: list[ScheduleCompactionRoundUseCaseInput] = []
        self._error = error

    def execute(self, request: ScheduleCompactionRoundUseCaseInput) -> ScheduleCompactionRoundUseCaseOutput:
        """Record the request and answer the round, or raise the configured error."""
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return ScheduleCompactionRoundUseCaseOutput(
            round_id=request.round_id,
            granted_table_uuids=["t-1"],
            picked=2,
            skipped_total=1,
            used_gb_hours=0.04,
            budget_gb_hours=0.05,
        )


def test_schedule_passes_the_round_and_now_and_returns_dict():
    """The activity runs the round named by the workflow at the workflow's now and returns its output."""
    schedule = FakeSchedule()

    result = CompactionRoundActivities(schedule=schedule).schedule_compaction_round(
        {"round_id": "compaction-rounds-1", "now": NOW.isoformat()}
    )

    assert schedule.requests == [ScheduleCompactionRoundUseCaseInput(round_id="compaction-rounds-1", now=NOW)]
    assert result == {
        "round_id": "compaction-rounds-1",
        "granted_table_uuids": ["t-1"],
        "picked": 2,
        "skipped_total": 1,
        "used_gb_hours": 0.04,
        "budget_gb_hours": 0.05,
    }


def test_a_stale_candidate_stays_retryable():
    """A candidate another writer changed propagates as is, so Temporal retries the round on fresh reads."""
    activities = CompactionRoundActivities(schedule=FakeSchedule(StaleCompactionCandidate("changed")))

    with pytest.raises(StaleCompactionCandidate):
        activities.schedule_compaction_round({"round_id": "r", "now": NOW.isoformat()})
