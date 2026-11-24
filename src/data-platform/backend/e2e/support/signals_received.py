"""Provide signals_received, which lists the signals a workflow got, oldest first."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.api.enums.v1 import EventType

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.temporal_session import TemporalSession


def signals_received(temporal: TemporalSession[Client], workflow_id: str) -> list[str]:
    """Return the name of each signal in the history of ``workflow_id``'s latest run."""

    async def names(client: Client) -> list[str]:
        history = await client.get_workflow_handle(workflow_id).fetch_history()
        return [
            event.workflow_execution_signaled_event_attributes.signal_name
            for event in history.events
            if event.event_type == EventType.EVENT_TYPE_WORKFLOW_EXECUTION_SIGNALED
        ]

    return temporal.run(names)
