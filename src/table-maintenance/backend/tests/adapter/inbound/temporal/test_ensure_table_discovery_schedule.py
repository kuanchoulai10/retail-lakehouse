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

from adapter.inbound.temporal.ensure_table_discovery_schedule import (
    ensure_table_discovery_schedule,
)
from adapter.temporal_contracts.table_discovery_workflow_input import (
    TableDiscoveryWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import TABLE_DISCOVERY_WORKFLOW
from application.domain.model.shared.workflow_ids import (
    TASK_QUEUE,
    table_discovery_schedule_id,
)
from tests.adapter.outbound.temporal.temporal_harness import harness  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Iterator

    from temporalio.client import ScheduleDescription

    from tests.adapter.outbound.temporal.temporal_harness import TemporalHarness

CATALOG = "ensure-test"


@pytest.fixture
def h(harness: TemporalHarness) -> Iterator[TemporalHarness]:  # noqa: F811
    yield harness

    async def delete() -> None:
        for catalog in (CATALOG, f"{CATALOG}-2"):
            handle = harness.client.get_schedule_handle(
                table_discovery_schedule_id(catalog)
            )
            try:
                await handle.delete()
            except RPCError:
                pass

    harness.bridge.run(delete)


def _ensure(
    h: TemporalHarness,
    catalogs: list[str],
    *,
    paused: bool,
    interval: timedelta = timedelta(minutes=10),
) -> None:
    h.bridge.run(
        lambda: ensure_table_discovery_schedule(
            h.client, catalogs, paused=paused, interval=interval
        )
    )


def _describe(h: TemporalHarness, catalog: str) -> ScheduleDescription:
    handle = h.client.get_schedule_handle(table_discovery_schedule_id(catalog))
    return h.bridge.run(handle.describe)


def test_discovery_schedule_created_once_and_paused_flag_applied(h):
    _ensure(h, [CATALOG], paused=True)

    desc = _describe(h, CATALOG)
    assert desc.schedule.state.paused is True
    assert desc.schedule.spec.intervals[0].every == timedelta(minutes=10)
    assert desc.schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    action = desc.schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow)
    assert action.workflow == TABLE_DISCOVERY_WORKFLOW
    assert action.id == table_discovery_schedule_id(CATALOG)
    assert action.task_queue == TASK_QUEUE
    assert isinstance(action.static_summary, Payload)
    summary = action.static_summary

    async def decoded_summary() -> list:
        return await h.client.data_converter.decode([summary], [str])

    assert h.bridge.run(decoded_summary) == [CATALOG]

    async def decoded_args() -> list:
        converter = h.client.data_converter
        return await converter.decode(action.args, [TableDiscoveryWorkflowInput])

    assert h.bridge.run(decoded_args) == [TableDiscoveryWorkflowInput(CATALOG)]

    _ensure(h, [CATALOG], paused=True, interval=timedelta(minutes=5))
    desc = _describe(h, CATALOG)
    assert desc.schedule.state.paused is True
    assert desc.schedule.spec.intervals[0].every == timedelta(minutes=5)

    _ensure(h, [CATALOG], paused=False)
    assert _describe(h, CATALOG).schedule.state.paused is False
    _ensure(h, [CATALOG], paused=False)
    assert _describe(h, CATALOG).schedule.state.paused is False


def test_one_schedule_per_catalog(h):
    _ensure(h, [CATALOG, f"{CATALOG}-2"], paused=False)
    assert _describe(h, CATALOG).schedule.state.paused is False
    assert _describe(h, f"{CATALOG}-2").schedule.state.paused is False
