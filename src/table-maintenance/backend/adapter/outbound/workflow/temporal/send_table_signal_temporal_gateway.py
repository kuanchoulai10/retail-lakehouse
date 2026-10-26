"""Define the SendTableSignalTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import RPCError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCStatusCode

from adapter.temporal_contracts.table_reconciliation_workflow_input import (
    TableReconciliationWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import TABLE_RECONCILIATION_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    TASK_QUEUE,
    table_reconciliation_workflow_id,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGatewayInput,
    )


class SendTableSignalTemporalGateway(SendTableSignalGateway):
    """Signal a table's reconciliation workflow through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        self._client = client
        self._bridge = bridge

    def send(self, input: SendTableSignalGatewayInput) -> None:  # noqa: A002
        """Signal the workflow, using signal-with-start when it may be missing."""
        self._bridge.run(lambda: self._send(input))

    async def _send(self, input: SendTableSignalGatewayInput) -> None:  # noqa: A002
        workflow_id = table_reconciliation_workflow_id(input.table_uuid)
        if input.start_if_missing:
            await self._client.start_workflow(
                TABLE_RECONCILIATION_WORKFLOW,
                TableReconciliationWorkflowInput(table_uuid=input.table_uuid),
                id=workflow_id,
                task_queue=TASK_QUEUE,
                start_signal=input.signal,
                start_signal_args=[input.payload],
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary=input.table_name,
            )
            return
        try:
            await self._client.get_workflow_handle(workflow_id).signal(
                input.signal, input.payload
            )
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
