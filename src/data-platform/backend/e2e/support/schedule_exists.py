"""Provide schedule_exists, which asks Temporal whether a schedule is there."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.service import RPCError, RPCStatusCode

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.temporal_session import TemporalSession


def schedule_exists(temporal: TemporalSession[Client], schedule_id: str) -> bool:
    """Return whether Temporal describes ``schedule_id``; NOT_FOUND is False, any other failure raises."""

    async def describe(client: Client) -> bool:
        try:
            await client.get_schedule_handle(schedule_id).describe()
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return False
            raise
        return True

    return temporal.run(describe)
