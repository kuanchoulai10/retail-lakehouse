"""Test UpdateDiscoveryScheduleTemporalGateway against a local Temporal server."""

from __future__ import annotations

from datetime import timedelta

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
    ScheduleState,
)

from adapter.outbound.discovery.temporal.update_discovery_schedule_temporal_gateway import (
    UpdateDiscoveryScheduleTemporalGateway,
)
from adapter.temporal_contracts.workflow_names import DISCOVERY_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    DISCOVERY_SCHEDULE_ID,
    TASK_QUEUE,
)
from application.port.outbound.discovery.update_discovery_schedule import (
    UpdateDiscoveryScheduleGatewayInput,
)


def test_update_without_schedule_does_not_raise(harness):
    gateway = UpdateDiscoveryScheduleTemporalGateway(harness.client, harness.bridge)
    gateway.update(UpdateDiscoveryScheduleGatewayInput(paused=True))


def test_update_pauses_and_unpauses_schedule(harness):
    async def create() -> None:
        await harness.client.create_schedule(
            DISCOVERY_SCHEDULE_ID,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    DISCOVERY_WORKFLOW,
                    {"catalog": "iceberg"},
                    id="table-discovery-scheduled",
                    task_queue=TASK_QUEUE,
                ),
                spec=ScheduleSpec(
                    intervals=[ScheduleIntervalSpec(every=timedelta(hours=1))]
                ),
                state=ScheduleState(paused=False),
            ),
        )

    async def paused() -> bool:
        desc = await harness.client.get_schedule_handle(
            DISCOVERY_SCHEDULE_ID
        ).describe()
        return desc.schedule.state.paused

    harness.bridge.run(create)
    gateway = UpdateDiscoveryScheduleTemporalGateway(harness.client, harness.bridge)
    gateway.update(UpdateDiscoveryScheduleGatewayInput(paused=True))
    assert harness.bridge.run(paused) is True
    gateway.update(UpdateDiscoveryScheduleGatewayInput(paused=False))
    assert harness.bridge.run(paused) is False
