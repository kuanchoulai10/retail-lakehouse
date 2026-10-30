"""Define ensure_table_discovery_schedule, which creates or updates the discovery schedules."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
)

from adapter.hybrid.temporal.contracts.shared import TASK_QUEUE
from adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
    table_discovery_schedule_id,
    table_discovery_summary,
)

if TYPE_CHECKING:
    from temporalio.client import Client, ScheduleUpdateInput

_NOTE = "set by table-maintenance worker start"


async def ensure_table_discovery_schedule(
    client: Client,
    catalogs: list[str],
    *,
    paused: bool,
    interval: timedelta = timedelta(minutes=10),
) -> None:
    """Create each catalog's discovery schedule, or bring an existing one up to date.

    A Temporal schedule holds one action, so every catalog gets its own schedule
    ``table-discovery:catalog={catalog}`` starting ``TableDiscoveryWorkflow`` for that catalog
    every ``interval``, skipping a firing while the previous run is still going.
    Calling it again is idempotent: it rewrites the action and the interval and
    applies ``paused``.
    """
    for catalog in catalogs:
        schedule_id = table_discovery_schedule_id(catalog)
        schedule = _schedule(catalog, paused=paused, interval=interval)
        try:
            await client.create_schedule(schedule_id, schedule)
            continue
        except ScheduleAlreadyRunningError:
            pass
        handle = client.get_schedule_handle(schedule_id)

        def replace(_: ScheduleUpdateInput, new: Schedule = schedule) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=new)

        await handle.update(replace)
        if paused:
            await handle.pause(note=_NOTE)
        else:
            await handle.unpause(note=_NOTE)


def _schedule(catalog: str, *, paused: bool, interval: timedelta) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            TABLE_DISCOVERY_WORKFLOW,
            TableDiscoveryWorkflowInput(catalog),
            id=table_discovery_schedule_id(catalog),
            task_queue=TASK_QUEUE,
            static_summary=table_discovery_summary(catalog, None),
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=interval)]),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
        state=ScheduleState(paused=paused, note=_NOTE),
    )
