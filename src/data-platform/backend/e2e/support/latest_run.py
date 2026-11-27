"""Provide latest_run, which reads the id, status and parent of a workflow's latest run."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.service import RPCError, RPCStatusCode

from e2e.support.workflow_run import WorkflowRun

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.temporal_session import TemporalSession


def latest_run(temporal: TemporalSession[Client], workflow_id: str) -> WorkflowRun | None:
    """Return ``workflow_id``'s latest run; None when it never ran, any other failure raises.

    A scenario that waits for a new run keeps the one before it acted and waits for another run id;
    the parent tells which workflow started the run as its child (a discovery round, for a catalog scan).
    """

    async def describe(client: Client) -> WorkflowRun | None:
        try:
            described = await client.get_workflow_handle(workflow_id).describe()
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return None
            raise
        assert described.status is not None, f"{workflow_id} run {described.run_id} has no status"
        return WorkflowRun(described.run_id, described.status, described.parent_id)

    return temporal.run(describe)
