"""Define the SendDiscoveryRequestTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy

from adapter.temporal_contracts.discovery_workflow_input import DiscoveryWorkflowInput
from adapter.temporal_contracts.workflow_names import DISCOVERY_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    TASK_QUEUE,
    discovery_adhoc_workflow_id,
)
from application.port.outbound.workflow.send_discovery_request import (
    SendDiscoveryRequestGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
    from application.port.outbound.workflow.send_discovery_request import (
        SendDiscoveryRequestGatewayInput,
    )


class SendDiscoveryRequestTemporalGateway(SendDiscoveryRequestGateway):
    """Start an ad-hoc discovery workflow through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        self._client = client
        self._bridge = bridge

    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Start the ad-hoc discovery workflow, reusing a running one."""
        self._bridge.run(lambda: self._send(input))

    async def _send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        await self._client.start_workflow(
            DISCOVERY_WORKFLOW,
            DiscoveryWorkflowInput(catalog=input.catalog, namespace=input.namespace),
            id=discovery_adhoc_workflow_id(input.catalog, input.namespace),
            task_queue=TASK_QUEUE,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
