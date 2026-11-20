"""Define the SendTableChangeTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio.client import RPCError
from temporalio.common import (
    SearchAttributeKey,
    SearchAttributePair,
    TypedSearchAttributes,
    WorkflowIDConflictPolicy,
)
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
    TableSearchAttribute,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationSignal,
    TableReconciliationWorkflowInput,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )
    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGatewayInput,
    )

_MAINTENANCE_REQUESTED = "maintenance_requested"
_TABLE_UUID_KEY = SearchAttributeKey.for_keyword(TableSearchAttribute.TABLE_UUID)
_TABLE_NAME_KEY = SearchAttributeKey.for_keyword(TableSearchAttribute.TABLE_NAME)

_SIGNAL_BY_CHANGE = {
    "updated": TableReconciliationSignal.TABLE_UPDATED,
    "policy_changed": TableReconciliationSignal.POLICY_CHANGED,
    "stopped": TableReconciliationSignal.STOP,
    _MAINTENANCE_REQUESTED: TableReconciliationSignal.TRIGGER_NOW,
    "reconcile_requested": TableReconciliationSignal.RECONCILE_NOW,
    "seen": TableReconciliationSignal.TABLE_SEEN,
    "managed": TableReconciliationSignal.TABLE_MANAGED,
}


class SendTableChangeTemporalGateway(SendTableChangeGateway):
    """Signal a table's reconciliation workflow through Temporal.

    Each change maps to one workflow signal. A managed table uses
    signal-with-start, so its workflow is started when it is missing; for a
    table that is not managed the signal only reaches a running workflow. A
    workflow it starts is tagged with the table's UUID and name; one already
    running keeps its own tags.
    """

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        """Keep the Temporal client that signals the workflow and the bridge that runs its async calls."""
        self._client = client
        self._bridge = bridge

    def send(self, input: SendTableChangeGatewayInput) -> None:  # noqa: A002
        """Signal the workflow, starting it first when the table is managed."""
        try:
            signal = _SIGNAL_BY_CHANGE[input.change]
        except KeyError:
            msg = f"unknown table change {input.change!r}"
            raise ValueError(msg) from None
        payload: dict[str, Any] = {}
        if input.change == _MAINTENANCE_REQUESTED:
            payload["operations"] = list(input.operations)
            if input.priority is not None:
                payload["priority"] = input.priority
        self._bridge.run(lambda: self._send(input, signal, payload))

    async def _send(
        self,
        input: SendTableChangeGatewayInput,  # noqa: A002
        signal: str,
        payload: dict[str, Any],
    ) -> None:
        workflow_id = table_reconciliation_workflow_id(input.table_uuid)
        if input.is_managed:
            await self._client.start_workflow(
                TABLE_RECONCILIATION_WORKFLOW,
                TableReconciliationWorkflowInput(table_uuid=input.table_uuid),
                id=workflow_id,
                task_queue=TASK_QUEUE,
                start_signal=signal,
                start_signal_args=[payload],
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary=input.table_name,
                search_attributes=TypedSearchAttributes(
                    [
                        SearchAttributePair(_TABLE_UUID_KEY, input.table_uuid),
                        SearchAttributePair(_TABLE_NAME_KEY, input.table_name),
                    ]
                ),
            )
            return
        try:
            await self._client.get_workflow_handle(workflow_id).signal(signal, payload)
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
