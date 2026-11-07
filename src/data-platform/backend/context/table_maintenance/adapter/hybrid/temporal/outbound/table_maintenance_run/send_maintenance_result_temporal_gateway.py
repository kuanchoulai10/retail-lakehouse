"""Define the SendMaintenanceResultTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    OperationResultSignal,
    TableMaintenanceSignal,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SendMaintenanceResultGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        SendMaintenanceResultGatewayInput,
    )


class SendMaintenanceResultTemporalGateway(SendMaintenanceResultGateway):
    """Deliver an operation result to a table maintenance workflow through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        """Keep the Temporal client that signals the workflow and the bridge that runs its async calls."""
        self._client = client
        self._bridge = bridge

    def send(self, input: SendMaintenanceResultGatewayInput) -> None:  # noqa: A002
        """Signal the table maintenance workflow, raising NotFoundError when it is gone."""
        self._bridge.run(lambda: self._send(input))

    async def _send(self, input: SendMaintenanceResultGatewayInput) -> None:  # noqa: A002
        handle = self._client.get_workflow_handle(input.execution_ref)
        result = OperationResultSignal(
            run_id=input.run_id,
            operation=input.operation,
            attempt=input.attempt,
            succeeded=input.succeeded,
            metrics=dict(input.metrics),
            error=input.error,
        )
        try:
            await handle.signal(TableMaintenanceSignal.OPERATION_RESULT, result)
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                msg = f"Table maintenance workflow {input.execution_ref} of run {input.run_id} not found"
                raise NotFoundError(msg) from error
            raise
