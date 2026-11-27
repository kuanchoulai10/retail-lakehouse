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
    table_discovery_catalog_workflow_id,
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
    """Start a requested table discovery workflow through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        """Keep the Temporal client that starts the workflow and the bridge that runs its async calls."""
        self._client = client
        self._bridge = bridge

    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Start the table discovery workflow, reusing a running one with the same id.

        A catalog-wide request runs under the catalog's one scan id, the one the discovery round
        starts its scans under, so it joins the catalog's scan already going, whoever started it,
        and its change id is not part of the id. A namespace request after a discovery policy change
        carries the change id in its id, so it joins only a run of that same change.
        """
        self._bridge.run(lambda: self._send(input))

    async def _send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        if input.namespace is None:
            workflow_id = table_discovery_catalog_workflow_id(input.catalog)
        else:
            workflow_id = table_discovery_adhoc_workflow_id(input.catalog, input.namespace, change_id=input.change_id)
        await self._client.start_workflow(
            TABLE_DISCOVERY_WORKFLOW,
            TableDiscoveryWorkflowInput(catalog=input.catalog, namespace=input.namespace),
            id=workflow_id,
            task_queue=TASK_QUEUE,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            static_summary=table_discovery_summary(input.catalog, input.namespace, adhoc=True),
        )
