"""Define the SendDiscoveryRequestTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import RPCError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoverySignal,
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
        """Start the table discovery workflow, or reach the one running under the same id.

        A catalog-wide request signal-with-starts the catalog's one scan id, the one the discovery
        round starts its scans under, with ``request_rescan``: it starts the scan when none is going,
        and otherwise asks the running scan, whoever started it, to scan once more when it finishes,
        so a request after a change is never served by a scan that read older policies. Its change
        id is not part of the id. A namespace request after a discovery policy change carries the
        change id in its id, so it joins only a run of that same change. A namespace request also
        signals ``request_rescan`` to the catalog's scan, without starting one: a catalog scan that
        read the policies before the change would otherwise decide the namespace's tables with
        them again. When no catalog scan is running that signal is dropped; any other failure of it
        is raised, after the namespace scan started.
        """
        self._bridge.run(lambda: self._send(input))

    async def _send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        if input.namespace is None:
            await self._client.start_workflow(
                TABLE_DISCOVERY_WORKFLOW,
                TableDiscoveryWorkflowInput(catalog=input.catalog),
                id=table_discovery_catalog_workflow_id(input.catalog),
                task_queue=TASK_QUEUE,
                start_signal=TableDiscoverySignal.REQUEST_RESCAN,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary=table_discovery_summary(input.catalog, None, adhoc=True),
            )
            return
        await self._client.start_workflow(
            TABLE_DISCOVERY_WORKFLOW,
            TableDiscoveryWorkflowInput(catalog=input.catalog, namespace=input.namespace),
            id=table_discovery_adhoc_workflow_id(input.catalog, input.namespace, change_id=input.change_id),
            task_queue=TASK_QUEUE,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            static_summary=table_discovery_summary(input.catalog, input.namespace, adhoc=True),
        )
        try:
            await self._client.get_workflow_handle(table_discovery_catalog_workflow_id(input.catalog)).signal(
                TableDiscoverySignal.REQUEST_RESCAN
            )
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
