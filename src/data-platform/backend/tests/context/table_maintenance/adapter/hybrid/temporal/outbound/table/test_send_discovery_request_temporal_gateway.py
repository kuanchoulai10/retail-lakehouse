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


def _wait_for(harness, query: str, expected: list[str]) -> list[str]:
    ids = sorted(_ids(harness, query))
    deadline = time.time() + 10
    while ids != expected and time.time() < deadline:
        time.sleep(0.1)
        ids = sorted(_ids(harness, query))
    return ids


def test_discovery_request_starts_one_workflow_per_scope(harness):
    """A namespace request starts an ad hoc scan; a catalog request starts the catalog's one scan."""
    gateway = SendDiscoveryRequestTemporalGateway(harness.client, harness.bridge)
    for _ in range(2):
        gateway.send(SendDiscoveryRequestGatewayInput("iceberg", "sales"))
    gateway.send(SendDiscoveryRequestGatewayInput("iceberg", None))
    ids = _wait_for(
        harness,
        "WorkflowId STARTS_WITH 'table-discovery:catalog=iceberg'",
        ["table-discovery:catalog=iceberg", "table-discovery:catalog=iceberg:namespace=sales:trigger=adhoc"],
    )
    assert ids == ["table-discovery:catalog=iceberg", "table-discovery:catalog=iceberg:namespace=sales:trigger=adhoc"]

    async def summaries() -> dict[str, str | None]:
        found = {}
        for workflow_id in ids:
            description = await harness.client.get_workflow_handle(workflow_id).describe()
            found[workflow_id] = await description.static_summary()
        return found

    assert harness.bridge.run(summaries) == {
        "table-discovery:catalog=iceberg": "iceberg · ad hoc",
        "table-discovery:catalog=iceberg:namespace=sales:trigger=adhoc": "iceberg.sales · ad hoc",
    }


def test_catalog_requests_join_the_catalog_scan_already_running(harness):
    """Every catalog request, after a policy change or not, joins the catalog's scan that is still going."""
    gateway = SendDiscoveryRequestTemporalGateway(harness.client, harness.bridge)
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None))

    async def run_id() -> str | None:
        return (await harness.client.get_workflow_handle("table-discovery:catalog=lake").describe()).run_id

    first = harness.bridge.run(run_id)
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None, change_id="c1"))
    gateway.send(SendDiscoveryRequestGatewayInput("lake", None, change_id="c2"))

    assert harness.bridge.run(run_id) == first
    only = ["table-discovery:catalog=lake"]
    assert _wait_for(harness, "WorkflowId STARTS_WITH 'table-discovery:catalog=lake'", only) == only


def test_namespace_change_requests_start_one_workflow_per_change(harness):
    """Each policy change of a namespace starts its own run, even while an earlier change's run is going."""
    gateway = SendDiscoveryRequestTemporalGateway(harness.client, harness.bridge)
    gateway.send(SendDiscoveryRequestGatewayInput("pond", "eu"))
    gateway.send(SendDiscoveryRequestGatewayInput("pond", "eu", change_id="c1"))
    gateway.send(SendDiscoveryRequestGatewayInput("pond", "eu", change_id="c2"))
    expected = [
        "table-discovery:catalog=pond:namespace=eu:trigger=adhoc",
        "table-discovery:catalog=pond:namespace=eu:trigger=policy-changed:change=c1",
        "table-discovery:catalog=pond:namespace=eu:trigger=policy-changed:change=c2",
    ]
    assert _wait_for(harness, "WorkflowId STARTS_WITH 'table-discovery:catalog=pond'", expected) == expected
