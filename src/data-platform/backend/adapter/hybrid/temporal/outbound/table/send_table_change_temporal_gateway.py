"""Define the SendTableChangeTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio.client import RPCError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCStatusCode

from adapter.hybrid.temporal.contracts.shared import TASK_QUEUE
from adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationSignal,
    TableReconciliationWorkflowInput,
    table_reconciliation_workflow_id,
)
from application.port.outbound.table import SendTableChangeGateway

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
    from application.port.outbound.table import SendTableChangeGatewayInput

_MAINTENANCE_REQUESTED = "maintenance_requested"

_SIGNAL_BY_CHANGE = {
    "updated": TableReconciliationSignal.TABLE_UPDATED,
    "settings_changed": TableReconciliationSignal.SETTINGS_CHANGED,
    "paused": TableReconciliationSignal.PAUSE,
    "resumed": TableReconciliationSignal.RESUME,
    "stopped": TableReconciliationSignal.STOP,
    _MAINTENANCE_REQUESTED: TableReconciliationSignal.TRIGGER_NOW,
}


class SendTableChangeTemporalGateway(SendTableChangeGateway):
    """Signal a table's reconciliation workflow through Temporal.

    Each change maps to one workflow signal. An enrolled table uses
    signal-with-start, so its workflow is started when it is missing; for a
    table that is not enrolled the signal only reaches a running workflow.
    """

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        self._client = client
        self._bridge = bridge

    def send(self, input: SendTableChangeGatewayInput) -> None:  # noqa: A002
        """Signal the workflow, starting it first when the table is enrolled."""
        try:
            signal = _SIGNAL_BY_CHANGE[input.change]
        except KeyError:
            msg = f"unknown table change {input.change!r}"
            raise ValueError(msg) from None
        payload: dict[str, Any] = (
            {"operations": list(input.operations)}
            if input.change == _MAINTENANCE_REQUESTED
            else {}
        )
        self._bridge.run(lambda: self._send(input, signal, payload))

    async def _send(
        self,
        input: SendTableChangeGatewayInput,  # noqa: A002
        signal: str,
        payload: dict[str, Any],
    ) -> None:
        workflow_id = table_reconciliation_workflow_id(input.table_uuid)
        if input.is_enrolled:
            await self._client.start_workflow(
                TABLE_RECONCILIATION_WORKFLOW,
                TableReconciliationWorkflowInput(table_uuid=input.table_uuid),
                id=workflow_id,
                task_queue=TASK_QUEUE,
                start_signal=signal,
                start_signal_args=[payload],
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary=input.table_name,
            )
            return
        try:
            await self._client.get_workflow_handle(workflow_id).signal(signal, payload)
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
