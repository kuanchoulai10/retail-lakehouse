"""Define the SendDiscoveryRequestTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
    table_discovery_adhoc_workflow_id,
    table_discovery_summary,
)
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )
    from context.table_maintenance.application.port.outbound.table import (
        SendDiscoveryRequestGatewayInput,
    )


class SendDiscoveryRequestTemporalGateway(SendDiscoveryRequestGateway):
    """Start an ad-hoc table discovery workflow through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        self._client = client
        self._bridge = bridge

    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Start the ad-hoc table discovery workflow, reusing a running one."""
        self._bridge.run(lambda: self._send(input))

    async def _send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        await self._client.start_workflow(
            TABLE_DISCOVERY_WORKFLOW,
            TableDiscoveryWorkflowInput(
                catalog=input.catalog, namespace=input.namespace
            ),
            id=table_discovery_adhoc_workflow_id(input.catalog, input.namespace),
            task_queue=TASK_QUEUE,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            static_summary=table_discovery_summary(
                input.catalog, input.namespace, adhoc=True
            ),
        )
