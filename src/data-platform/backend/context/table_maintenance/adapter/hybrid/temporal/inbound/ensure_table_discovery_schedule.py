"""Define ensure_table_discovery_schedule, which creates or updates the one discovery schedule."""

from __future__ import annotations

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

if TYPE_CHECKING:
    from datetime import timedelta

    from temporalio.client import Client, ScheduleUpdateInput

_NOTE = "set by table-maintenance worker start"


async def ensure_table_discovery_schedule(client: Client, *, interval: timedelta) -> None:
    """Create the schedule ``table-discovery``, or bring the existing one up to date and unpause it.

    It starts ``TableDiscoveryRoundWorkflow`` under ``table-discovery:round`` every ``interval`` and
    skips a firing while the previous round is still going; a round only starts its scans, so it
    ends quickly. Calling it again rewrites the action and the interval, and unpauses a schedule
    paused by hand.
    """
    schedule = Schedule(
        action=ScheduleActionStartWorkflow(
            TABLE_DISCOVERY_ROUND_WORKFLOW,
            id=TABLE_DISCOVERY_ROUND_WORKFLOW_ID,
            task_queue=TASK_QUEUE,
            static_summary=TABLE_DISCOVERY_ROUND_SUMMARY,
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=interval)]),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
        state=ScheduleState(paused=False, note=_NOTE),
    )
    try:
        await client.create_schedule(TABLE_DISCOVERY_SCHEDULE_ID, schedule)
    except ScheduleAlreadyRunningError:
        pass
    else:
        return
    handle = client.get_schedule_handle(TABLE_DISCOVERY_SCHEDULE_ID)

    def replace(_: ScheduleUpdateInput) -> ScheduleUpdate:
        return ScheduleUpdate(schedule=schedule)

    await handle.update(replace)
    await handle.unpause(note=_NOTE)
