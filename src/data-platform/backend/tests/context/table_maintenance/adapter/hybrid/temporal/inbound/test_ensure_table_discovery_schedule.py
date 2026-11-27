"""Test ensure_table_discovery_schedule against a local Temporal dev server."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.api.common.v1 import Payload
from temporalio.client import (
    RPCError,
    ScheduleActionStartWorkflow,
    ScheduleOverlapPolicy,
)

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TABLE_DISCOVERY_ROUND_SUMMARY,
    TABLE_DISCOVERY_ROUND_WORKFLOW,
    TABLE_DISCOVERY_ROUND_WORKFLOW_ID,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
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
    """Provide the Temporal test harness, with no discovery schedule before or after the test."""

    async def delete() -> None:
        try:
            await harness.client.get_schedule_handle(TABLE_DISCOVERY_SCHEDULE_ID).delete()
        except RPCError:
            pass

    harness.bridge.run(delete)
    yield harness
    harness.bridge.run(delete)


def _ensure(h: TemporalHarness, interval: timedelta) -> None:
    h.bridge.run(lambda: ensure_table_discovery_schedule(h.client, interval=interval))


def _describe(h: TemporalHarness) -> ScheduleDescription:
    return h.bridge.run(h.client.get_schedule_handle(TABLE_DISCOVERY_SCHEDULE_ID).describe)


def test_a_missing_schedule_is_created_running_the_round(h):
    """The one discovery schedule starts the round every interval, skips an overlap and runs unpaused."""
    _ensure(h, timedelta(minutes=10))

    desc = _describe(h)
    assert desc.schedule.state.paused is False
    assert [spec.every for spec in desc.schedule.spec.intervals] == [timedelta(minutes=10)]
    assert desc.schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    action = desc.schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow)
    assert action.workflow == TABLE_DISCOVERY_ROUND_WORKFLOW
    assert action.id == TABLE_DISCOVERY_ROUND_WORKFLOW_ID
    assert action.task_queue == TASK_QUEUE
    assert action.args == []
    assert isinstance(action.static_summary, Payload)
    summary = action.static_summary

    async def decoded_summary() -> list:
        return await h.client.data_converter.decode([summary], [str])

    assert h.bridge.run(decoded_summary) == [TABLE_DISCOVERY_ROUND_SUMMARY]


def test_an_existing_schedule_takes_the_new_interval_and_is_unpaused(h):
    """Ensuring again rewrites the interval and unpauses a schedule paused by hand."""
    _ensure(h, timedelta(minutes=10))
    h.bridge.run(lambda: h.client.get_schedule_handle(TABLE_DISCOVERY_SCHEDULE_ID).pause(note="by hand"))

    _ensure(h, timedelta(minutes=5))

    desc = _describe(h)
    assert desc.schedule.state.paused is False
    assert [spec.every for spec in desc.schedule.spec.intervals] == [timedelta(minutes=5)]
    action = desc.schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow)
    assert action.workflow == TABLE_DISCOVERY_ROUND_WORKFLOW
