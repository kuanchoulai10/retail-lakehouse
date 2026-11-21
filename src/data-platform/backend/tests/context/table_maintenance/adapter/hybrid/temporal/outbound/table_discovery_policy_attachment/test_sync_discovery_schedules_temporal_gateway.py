"""Test SyncDiscoverySchedulesTemporalGateway against a local Temporal dev server.

The dev server is shared by the whole session, so each test uses catalog names of its own and deletes
its schedules at the end.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.api.common.v1 import Payload
from temporalio.client import (
    RPCError,
    RPCStatusCode,
    ScheduleActionStartWorkflow,
    ScheduleOverlapPolicy,
)

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
    table_discovery_schedule_id,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesTemporalGateway,
    table_discovery_schedule,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesGatewayInput,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from temporalio.client import ScheduleDescription

    from tests.context.table_maintenance.adapter.hybrid.temporal.outbound.shared.temporal_harness import (
        TemporalHarness,
    )

UNRELATED_SCHEDULE_ID = "sync-test-unrelated-schedule"


class _Schedules:
    """Reach the dev server's schedules for one test, and delete the ones it made at the end."""

    def __init__(self, harness: TemporalHarness) -> None:
        self.harness = harness
        self.made: set[str] = set()

    def gateway(self, *, interval: timedelta = timedelta(minutes=10)) -> SyncDiscoverySchedulesTemporalGateway:
        return SyncDiscoverySchedulesTemporalGateway(self.harness.client, self.harness.bridge, interval=interval)

    def sync(self, catalogs: tuple[str, ...], removed: tuple[str, ...] = (), **kwargs: timedelta) -> None:
        self.made |= {table_discovery_schedule_id(c) for c in catalogs}
        self.gateway(**kwargs).sync(SyncDiscoverySchedulesGatewayInput(catalogs=catalogs, removed=removed))

    def create_discovery_schedule(self, catalog: str) -> None:
        """Create a catalog's discovery schedule straight through the client."""
        self.create(table_discovery_schedule_id(catalog), catalog)

    def create(self, schedule_id: str, catalog: str) -> None:
        self.made.add(schedule_id)
        schedule = table_discovery_schedule(catalog, interval=timedelta(minutes=10))
        self.harness.bridge.run(lambda: self.harness.client.create_schedule(schedule_id, schedule))

    def describe(self, catalog: str) -> ScheduleDescription:
        handle = self.harness.client.get_schedule_handle(table_discovery_schedule_id(catalog))
        return self.harness.bridge.run(handle.describe)

    def exists(self, schedule_id: str) -> bool:
        try:
            self.harness.bridge.run(self.harness.client.get_schedule_handle(schedule_id).describe)
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return False
            raise
        return True

    def listed_until(self, wanted: set[str], gateway: SyncDiscoverySchedulesTemporalGateway) -> tuple[str, ...]:
        """List the scheduled catalogs until ``wanted`` shows up: the listing lags behind a create."""
        deadline = time.time() + 15
        listed = gateway.list_scheduled_catalogs()
        while not wanted <= set(listed) and time.time() < deadline:
            time.sleep(0.2)
            listed = gateway.list_scheduled_catalogs()
        return listed

    def delete_made(self) -> None:
        async def delete() -> None:
            for schedule_id in self.made:
                try:
                    await self.harness.client.get_schedule_handle(schedule_id).delete()
                except RPCError:
                    pass

        self.harness.bridge.run(delete)


@pytest.fixture
def h(harness: TemporalHarness) -> Iterator[_Schedules]:
    """Provide the schedules of the session's dev server, cleaning up what the test made."""
    schedules = _Schedules(harness)
    yield schedules
    schedules.delete_made()


def test_sync_creates_wanted_and_deletes_removed_schedules(h: _Schedules) -> None:
    """A wanted catalog gets its schedule and a removed catalog's schedule is deleted."""
    h.create_discovery_schedule("sync-old")

    h.sync(("sync-new",), removed=("sync-old",))

    assert h.exists(table_discovery_schedule_id("sync-new"))
    assert not h.exists(table_discovery_schedule_id("sync-old"))


def test_the_schedule_starts_the_discovery_of_its_catalog(h: _Schedules) -> None:
    """The schedule runs every interval, skips overlaps, is not paused and starts the catalog's discovery."""
    h.sync(("sync-action",))

    desc = h.describe("sync-action")
    assert desc.schedule.state.paused is False
    assert desc.schedule.spec.intervals[0].every == timedelta(minutes=10)
    assert desc.schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    action = desc.schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow)
    assert (action.workflow, action.id, action.task_queue) == (
        TABLE_DISCOVERY_WORKFLOW,
        table_discovery_schedule_id("sync-action"),
        TASK_QUEUE,
    )
    assert isinstance(action.static_summary, Payload)
    summary = action.static_summary
    converter = h.harness.client.data_converter

    async def decoded() -> tuple[list, list]:
        return await converter.decode([summary], [str]), await converter.decode(
            action.args, [TableDiscoveryWorkflowInput]
        )

    assert h.harness.bridge.run(decoded) == (["sync-action"], [TableDiscoveryWorkflowInput("sync-action")])


def test_sync_rewrites_the_interval_and_unpauses(h: _Schedules) -> None:
    """A schedule that exists takes the current interval and runs again when it was paused by hand."""
    h.sync(("sync-interval",))
    handle = h.harness.client.get_schedule_handle(table_discovery_schedule_id("sync-interval"))
    h.harness.bridge.run(lambda: handle.pause(note="by hand"))

    h.sync(("sync-interval",), interval=timedelta(minutes=5))

    desc = h.describe("sync-interval")
    assert desc.schedule.state.paused is False
    assert desc.schedule.spec.intervals[0].every == timedelta(minutes=5)


def test_sync_leaves_other_schedules_alone(h: _Schedules) -> None:
    """A discovery schedule neither wanted nor removed, and a schedule of another kind, both survive."""
    h.create_discovery_schedule("sync-bystander")
    h.create(UNRELATED_SCHEDULE_ID, "sync-unrelated")

    h.sync(("sync-wanted",), removed=("sync-gone",))

    assert h.exists(table_discovery_schedule_id("sync-bystander"))
    assert h.exists(UNRELATED_SCHEDULE_ID)


def test_removing_a_catalog_without_a_schedule_does_nothing(h: _Schedules) -> None:
    """Deleting a schedule that is already gone is not an error."""
    h.sync((), removed=("sync-never-scheduled",))

    assert not h.exists(table_discovery_schedule_id("sync-never-scheduled"))


def test_list_names_the_catalogs_of_the_discovery_schedules(h: _Schedules) -> None:
    """The listing gives each discovery schedule's catalog, sorted, and no schedule of another kind."""
    h.create_discovery_schedule("sync-list-b")
    h.create_discovery_schedule("sync-list-a")
    h.create(UNRELATED_SCHEDULE_ID, "sync-list-unrelated")

    listed = h.listed_until({"sync-list-a", "sync-list-b"}, h.gateway())

    assert {"sync-list-a", "sync-list-b"} <= set(listed)
    assert list(listed) == sorted(listed)
    assert UNRELATED_SCHEDULE_ID not in listed
    assert not any(c.startswith("table-discovery:") for c in listed)
