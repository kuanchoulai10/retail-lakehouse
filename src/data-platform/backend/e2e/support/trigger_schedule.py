"""Provide trigger_schedule, which has Temporal run a schedule's action now."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import ScheduleOverlapPolicy

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.temporal_session import TemporalSession


def trigger_schedule(temporal: TemporalSession[Client], schedule_id: str) -> None:
    """Start ``schedule_id``'s action now, as one extra firing beside its interval.

    The trigger buffers one firing behind an action still running (``BUFFER_ONE``) rather than taking
    the schedule's own overlap policy, so a ``SKIP`` schedule never drops it.
    """

    async def trigger(client: Client) -> None:
        await client.get_schedule_handle(schedule_id).trigger(overlap=ScheduleOverlapPolicy.BUFFER_ONE)

    temporal.run(trigger)
