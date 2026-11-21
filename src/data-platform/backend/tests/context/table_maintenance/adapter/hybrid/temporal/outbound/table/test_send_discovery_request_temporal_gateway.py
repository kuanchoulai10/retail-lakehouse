"""Test SendDiscoveryRequestTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time

from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
)
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGatewayInput,
)


def _ids(harness, query: str) -> list[str]:
    async def listing() -> list[str]:
        return [w.id async for w in harness.client.list_workflows(query)]

    return harness.bridge.run(listing)


def test_discovery_request_starts_one_adhoc_workflow(harness):
    """A discovery request starts one ad hoc discovery workflow with the catalog and namespace in its id and summary."""
    gateway = SendDiscoveryRequestTemporalGateway(harness.client, harness.bridge)
    for _ in range(2):
        gateway.send(SendDiscoveryRequestGatewayInput("iceberg", "sales"))
    gateway.send(SendDiscoveryRequestGatewayInput("iceberg", None))
    query = "WorkflowId STARTS_WITH 'table-discovery:catalog=iceberg'"
    ids = sorted(_ids(harness, query))
    deadline = time.time() + 10
    while len(ids) < 2 and time.time() < deadline:
        time.sleep(0.1)
        ids = sorted(_ids(harness, query))
    assert ids == [
        "table-discovery:catalog=iceberg:namespace=sales:trigger=adhoc",
        "table-discovery:catalog=iceberg:trigger=adhoc",
    ]

    async def summaries() -> dict[str, str | None]:
        found = {}
        for workflow_id in ids:
            description = await harness.client.get_workflow_handle(workflow_id).describe()
            found[workflow_id] = await description.static_summary()
        return found

    assert harness.bridge.run(summaries) == {
        "table-discovery:catalog=iceberg:namespace=sales:trigger=adhoc": ("iceberg.sales · ad hoc"),
        "table-discovery:catalog=iceberg:trigger=adhoc": "iceberg · ad hoc",
    }


def test_policy_change_requests_start_one_workflow_per_change(harness):
    """Each policy change starts its own run, even while the run of an earlier change or an event is still going."""
    gateway = SendDiscoveryRequestTemporalGateway(harness.client, harness.bridge)
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None))
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None, change_id="c1"))
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None, change_id="c2"))
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None, change_id="s1", retires_schedule=True))
    query = "WorkflowId STARTS_WITH 'table-discovery:catalog=lake'"
    expected = [
        "table-discovery:catalog=lake:trigger=adhoc",
        "table-discovery:catalog=lake:trigger=policy-changed:change=c1",
        "table-discovery:catalog=lake:trigger=policy-changed:change=c2",
        "table-discovery:catalog=lake:trigger=schedule-retired:change=s1",
    ]
    ids = sorted(_ids(harness, query))
    deadline = time.time() + 10
    while ids != expected and time.time() < deadline:
        time.sleep(0.1)
        ids = sorted(_ids(harness, query))
    assert ids == expected
