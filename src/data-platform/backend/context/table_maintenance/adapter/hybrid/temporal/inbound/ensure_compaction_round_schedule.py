"""Define ensure_compaction_round_schedule, which creates or updates the compaction round schedule."""

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

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    COMPACTION_ROUND_SCHEDULE_ID,
    COMPACTION_ROUND_WORKFLOW,
    CompactionRoundWorkflowInput,
    compaction_round_summary,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import CompactionRoundActivityPolicy

if TYPE_CHECKING:
    from temporalio.client import Client, ScheduleUpdateInput

_NOTE = "set by table-maintenance worker start"
# Room for the round's workflow tasks on top of its activities' worst case.
_WORKFLOW_TASK_SLACK = timedelta(minutes=1)


async def ensure_compaction_round_schedule(client: Client, *, interval: timedelta, budget_gb_hours: float) -> None:
    """Create the one compaction round schedule, or bring it up to date.

    The schedule ``compaction-rounds`` starts ``CompactionRoundWorkflow`` every
    ``interval``, skipping a firing while the previous round still runs, so
    there is one scheduler. A round runs for at most three intervals, or for
    its activities' worst case (``CompactionRoundActivityPolicy``) plus a
    minute when that is longer: a round wedged on a failing workflow task then
    ends and the next firing is no longer skipped, yet a round is never ended
    while an activity attempt could still save grants it would not signal.
    Calling it again is idempotent: it rewrites the
    action, the interval and the summary (which shows ``budget_gb_hours``) and
    unpauses a schedule paused by hand.
    """
    schedule = _schedule(interval=interval, budget_gb_hours=budget_gb_hours)
    try:
        await client.create_schedule(COMPACTION_ROUND_SCHEDULE_ID, schedule)
        return
    except ScheduleAlreadyRunningError:
        pass
    handle = client.get_schedule_handle(COMPACTION_ROUND_SCHEDULE_ID)

    def replace(_: ScheduleUpdateInput) -> ScheduleUpdate:
        return ScheduleUpdate(schedule=schedule)

    await handle.update(replace)
    await handle.unpause(note=_NOTE)


def _schedule(*, interval: timedelta, budget_gb_hours: float) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            COMPACTION_ROUND_WORKFLOW,
            CompactionRoundWorkflowInput(),
            id=COMPACTION_ROUND_SCHEDULE_ID,
            task_queue=TASK_QUEUE,
            static_summary=compaction_round_summary(budget_gb_hours),
            execution_timeout=max(3 * interval, CompactionRoundActivityPolicy().worst_case() + _WORKFLOW_TASK_SLACK),
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=interval)]),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
        state=ScheduleState(paused=False, note=_NOTE),
    )
