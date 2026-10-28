"""Define the SendDiscoveryRequestTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy

from adapter.hybrid.temporal.contracts import (
    table_discovery_summary,
    TableDiscoveryWorkflowInput,
    TABLE_DISCOVERY_WORKFLOW,
    TASK_QUEUE,
    table_discovery_adhoc_workflow_id,
)
from application.port.outbound.table import SendDiscoveryRequestGateway

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
    from application.port.outbound.table import SendDiscoveryRequestGatewayInput


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
