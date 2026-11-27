"""Provide scheduled_workflows, which lists the workflows a schedule's recent actions started."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import ScheduleActionExecutionStartWorkflow

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.temporal_session import TemporalSession


def scheduled_workflows(temporal: TemporalSession[Client], schedule_id: str) -> list[str]:
    """Return the workflow id each of the schedule's recent workflow-starting actions started, oldest first.

    Triggers count too.

    Temporal suffixes the action's workflow id with the time the action was scheduled for, so each
    round of ``table-discovery`` has an id of its own, ``table-discovery:round-<time>``, which its
    children name as their parent.
    """

    async def describe(client: Client) -> list[str]:
        described = await client.get_schedule_handle(schedule_id).describe()
        actions = [result.action for result in described.info.recent_actions]
        return [action.workflow_id for action in actions if isinstance(action, ScheduleActionExecutionStartWorkflow)]

    return temporal.run(describe)
