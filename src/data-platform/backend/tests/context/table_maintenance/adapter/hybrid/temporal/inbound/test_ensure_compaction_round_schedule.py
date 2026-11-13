"""Test ensure_compaction_round_schedule against a local Temporal dev server."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.client import (
    RPCError,
    ScheduleActionStartWorkflow,
    ScheduleOverlapPolicy,
)

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    COMPACTION_ROUND_SCHEDULE_ID,
    COMPACTION_ROUND_WORKFLOW,
    CompactionRoundWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_compaction_round_schedule,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.outbound.shared.temporal_harness import (
    harness,  # noqa: F401
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from temporalio.client import ScheduleDescription

    from tests.context.table_maintenance.adapter.hybrid.temporal.outbound.shared.temporal_harness import (
        TemporalHarness,
    )


@pytest.fixture
def h(harness: TemporalHarness) -> Iterator[TemporalHarness]:  # noqa: F811
    """Provide the Temporal test harness and delete the round schedule afterwards."""
    yield harness

    async def delete() -> None:
        try:
            await harness.client.get_schedule_handle(COMPACTION_ROUND_SCHEDULE_ID).delete()
        except RPCError:
            pass

    harness.bridge.run(delete)


def _ensure(h: TemporalHarness, *, interval: timedelta, budget_gb_hours: float = 0.05) -> None:
    h.bridge.run(lambda: ensure_compaction_round_schedule(h.client, interval=interval, budget_gb_hours=budget_gb_hours))


def _describe(h: TemporalHarness) -> ScheduleDescription:
    return h.bridge.run(h.client.get_schedule_handle(COMPACTION_ROUND_SCHEDULE_ID).describe)


def test_round_schedule_starts_one_round_every_interval_and_skips_overlaps(h):
    """One schedule starts a round every interval, never two at once, with the budget in its summary."""
    _ensure(h, interval=timedelta(seconds=120))

    desc = _describe(h)
    assert desc.schedule.state.paused is False
    assert desc.schedule.spec.intervals[0].every == timedelta(seconds=120)
    assert desc.schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    action = desc.schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow)
    assert (action.workflow, action.id, action.task_queue) == (
        COMPACTION_ROUND_WORKFLOW,
        COMPACTION_ROUND_SCHEDULE_ID,
        TASK_QUEUE,
    )
    summary = action.static_summary
    assert summary is not None

    async def decoded() -> tuple[list, list]:
        converter = h.client.data_converter
        return (
            await converter.decode([summary], [str]),
            await converter.decode(action.args, [CompactionRoundWorkflowInput]),
        )

    assert h.bridge.run(decoded) == (["compaction round · budget 0.05 GB·h"], [CompactionRoundWorkflowInput()])


def test_ensure_schedule_is_idempotent(h):
    """Ensuring again updates the interval and budget and unpauses a schedule paused by hand."""
    _ensure(h, interval=timedelta(seconds=120))
    h.bridge.run(lambda: h.client.get_schedule_handle(COMPACTION_ROUND_SCHEDULE_ID).pause(note="by hand"))

    _ensure(h, interval=timedelta(seconds=60), budget_gb_hours=0.2)

    desc = _describe(h)
    assert desc.schedule.state.paused is False
    assert desc.schedule.spec.intervals[0].every == timedelta(seconds=60)
