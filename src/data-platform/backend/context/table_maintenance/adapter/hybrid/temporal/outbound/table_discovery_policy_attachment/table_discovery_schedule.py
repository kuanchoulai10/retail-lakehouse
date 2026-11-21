"""Define table_discovery_schedule, the Temporal schedule that scans one catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
)

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
    table_discovery_schedule_id,
    table_discovery_summary,
)

if TYPE_CHECKING:
    from datetime import timedelta

_NOTE = "set by the discovery schedule sync"


def table_discovery_schedule(catalog: str, *, interval: timedelta) -> Schedule:
    """Return the schedule that starts ``TableDiscoveryWorkflow`` for ``catalog`` every ``interval``.

    A Temporal schedule holds one action, so each catalog has its own. A firing is skipped while the
    previous run is still going, and the schedule is created running.
    """
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
        state=ScheduleState(paused=False, note=_NOTE),
    )
