"""Test SendDiscoveryRequestTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time

from adapter.outbound.workflow.temporal.send_discovery_request_temporal_gateway import (
    SendDiscoveryRequestTemporalGateway,
)
from application.port.outbound.workflow.send_discovery_request import (
    SendDiscoveryRequestGatewayInput,
)


def _ids(harness, query: str) -> list[str]:
    async def listing() -> list[str]:
        return [w.id async for w in harness.client.list_workflows(query)]

    return harness.bridge.run(listing)


def test_discovery_request_starts_one_adhoc_workflow(harness):
    gateway = SendDiscoveryRequestTemporalGateway(harness.client, harness.bridge)
    for _ in range(2):
        gateway.send(SendDiscoveryRequestGatewayInput("iceberg", "sales"))
    gateway.send(SendDiscoveryRequestGatewayInput("iceberg", None))
    time.sleep(1)
    ids = sorted(_ids(harness, "WorkflowId STARTS_WITH 'table-discovery-adhoc-'"))
    assert ids == [
        "table-discovery-adhoc-iceberg-all",
        "table-discovery-adhoc-iceberg-sales",
    ]
