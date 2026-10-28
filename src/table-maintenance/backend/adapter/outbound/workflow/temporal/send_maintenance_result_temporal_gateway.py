"""Define the SendMaintenanceResultTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from adapter.temporal_contracts.operation_result_signal import OperationResultSignal
from application.domain.model.shared.workflow_ids import SIGNAL_OPERATION_RESULT
from application.exceptions import NotFoundError
from application.port.outbound.workflow.send_maintenance_result import (
    SendMaintenanceResultGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
    from application.port.outbound.workflow.send_maintenance_result import (
        SendMaintenanceResultGatewayInput,
    )


class SendMaintenanceResultTemporalGateway(SendMaintenanceResultGateway):
    """Deliver an operation result to a table maintenance workflow through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
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
            await handle.signal(SIGNAL_OPERATION_RESULT, result)
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                msg = (
                    f"Table maintenance workflow {input.execution_ref} of run "
                    f"{input.run_id} not found"
                )
                raise NotFoundError(msg) from error
            raise
