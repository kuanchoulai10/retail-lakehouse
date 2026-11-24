"""Provide reconciliation_running, which asks Temporal whether a table's reconciliation workflow runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError, RPCStatusCode

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.temporal_session import TemporalSession


def reconciliation_running(temporal: TemporalSession[Client], table_uuid: str) -> bool:
    """Return whether ``table-reconciliation:table-uuid=<uuid>`` is running (False when Temporal has none)."""

    async def describe(client: Client) -> bool:
        handle = client.get_workflow_handle(f"table-reconciliation:table-uuid={table_uuid}")
        try:
            return (await handle.describe()).status == WorkflowExecutionStatus.RUNNING
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return False
            raise

    return temporal.run(describe)
