"""Test UpdateTableDiscoveryScheduleTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time
from datetime import timedelta

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
    ScheduleState,
)

from adapter.outbound.table_discovery_settings.temporal.update_table_discovery_schedule_temporal_gateway import (
    UpdateTableDiscoveryScheduleTemporalGateway,
)
from adapter.temporal_contracts.workflow_names import TABLE_DISCOVERY_WORKFLOW
from application.domain.model.shared.workflow_ids import (
    TASK_QUEUE,
    table_discovery_schedule_id,
)
from application.port.outbound.table_discovery_settings.update_table_discovery_schedule import (
    UpdateTableDiscoveryScheduleGatewayInput,
)

CATALOGS = ("gw-a", "gw-b")
OTHER_SCHEDULE_ID = "unrelated-schedule"


def test_update_without_schedule_does_not_raise(harness):
    gateway = UpdateTableDiscoveryScheduleTemporalGateway(
        harness.client, harness.bridge
    )
    gateway.update(UpdateTableDiscoveryScheduleGatewayInput(paused=True))


def _schedule(catalog: str) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            TABLE_DISCOVERY_WORKFLOW,
            {"catalog": catalog},
            id=table_discovery_schedule_id(catalog),
            task_queue=TASK_QUEUE,
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(hours=1))]),
        state=ScheduleState(paused=False),
    )


def test_update_pauses_and_unpauses_every_catalog_schedule(harness):
    ids = [table_discovery_schedule_id(c) for c in CATALOGS]

    async def create() -> None:
        for catalog, schedule_id in zip(CATALOGS, ids, strict=True):
            await harness.client.create_schedule(schedule_id, _schedule(catalog))
        await harness.client.create_schedule(OTHER_SCHEDULE_ID, _schedule("other"))

    async def listed() -> set[str]:
        return {s.id async for s in await harness.client.list_schedules()}

    async def paused(schedule_id: str) -> bool:
        desc = await harness.client.get_schedule_handle(schedule_id).describe()
        return desc.schedule.state.paused

    async def delete() -> None:
        for schedule_id in [*ids, OTHER_SCHEDULE_ID]:
            await harness.client.get_schedule_handle(schedule_id).delete()

    harness.bridge.run(create)
    try:
        deadline = time.monotonic() + 15
        while not set(ids) <= harness.bridge.run(listed):
            assert time.monotonic() < deadline, "schedules never became visible"
            time.sleep(0.2)
        gateway = UpdateTableDiscoveryScheduleTemporalGateway(
            harness.client, harness.bridge
        )
        gateway.update(UpdateTableDiscoveryScheduleGatewayInput(paused=True))
        assert [harness.bridge.run(lambda i=i: paused(i)) for i in ids] == [True, True]
        assert harness.bridge.run(lambda: paused(OTHER_SCHEDULE_ID)) is False
        gateway.update(UpdateTableDiscoveryScheduleGatewayInput(paused=False))
        assert [harness.bridge.run(lambda i=i: paused(i)) for i in ids] == [
            False,
            False,
        ]
    finally:
        harness.bridge.run(delete)
