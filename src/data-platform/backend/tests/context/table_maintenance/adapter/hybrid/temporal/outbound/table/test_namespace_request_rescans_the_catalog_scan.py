"""Test that a namespace discovery request asks a running catalog scan to scan again, on a local dev server.

A catalog scan reads the discovery policies once, when it starts, then decides each table it lists
with them; one that started before a namespace's policy changed would undo the namespace scan's
newer decision. These run the real ``TableDiscoveryWorkflow`` with a scripted sync that holds the
first catalog-wide sync until the test releases it.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from temporalio import activity
from temporalio.client import WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TableDiscoveryActivity,
    table_discovery_adhoc_workflow_id,
    table_discovery_catalog_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableDiscoveryWorkflow,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
)
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGatewayInput,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from temporalio.client import Client

CATALOG = "lake"
CATALOG_SCAN = table_discovery_catalog_workflow_id(CATALOG)


@dataclass
class _Scans:
    """A dev server running the real discovery workflow, with a scripted sync that records each scope."""

    client: Client
    bridge: AsyncLoopBridge
    gateway: SendDiscoveryRequestTemporalGateway
    hold_first_catalog_sync: threading.Event
    synced: list[dict[str, Any]] = field(default_factory=list)

    def catalog_syncs(self) -> int:
        """Return how many catalog-wide syncs ran."""
        return sum(1 for request in self.synced if request["namespace"] is None)

    def wait_until(self, check: Callable[[], bool], what: str) -> None:
        """Wait up to 20 s for ``check`` to hold."""
        deadline = time.monotonic() + 20
        while not check():
            if time.monotonic() > deadline:
                raise AssertionError(f"never saw {what}; synced {self.synced}")
            time.sleep(0.05)

    def runs(self, workflow_id: str) -> list[WorkflowExecutionStatus | None]:
        """Return the status of every run of ``workflow_id``."""

        async def listing() -> list[WorkflowExecutionStatus | None]:
            return [w.status async for w in self.client.list_workflows(f"WorkflowId = '{workflow_id}'")]

        return self.bridge.run(listing)


@pytest.fixture
def scans() -> Iterator[_Scans]:
    """Provide a dev server whose worker runs the real discovery workflow and a scripted sync."""
    bridge = AsyncLoopBridge()
    env = bridge.run(WorkflowEnvironment.start_local, timeout=300)
    hold = threading.Event()
    synced: list[dict[str, Any]] = []

    @activity.defn(name=TableDiscoveryActivity.SYNC_DISCOVERED_TABLES)
    async def sync_discovered_tables(request: dict[str, Any]) -> dict[str, Any]:
        synced.append(request)
        first_catalog_sync = request["namespace"] is None and sum(r["namespace"] is None for r in synced) == 1
        while first_catalog_sync and hold.is_set():
            await asyncio.sleep(0.05)
        return {"synced": len(synced)}

    workers: list[Worker] = []
    tasks: list[asyncio.Task] = []

    async def start() -> None:
        worker = Worker(
            env.client, task_queue=TASK_QUEUE, workflows=[TableDiscoveryWorkflow], activities=[sync_discovered_tables]
        )
        workers.append(worker)
        tasks.append(asyncio.ensure_future(worker.run()))

    bridge.run(start)
    try:
        yield _Scans(env.client, bridge, SendDiscoveryRequestTemporalGateway(env.client, bridge), hold, synced)
    finally:
        hold.clear()

        async def stop() -> None:
            await workers[0].shutdown()
            await asyncio.gather(*tasks)
            await env.shutdown()

        bridge.run(stop, timeout=60)
        bridge.close()


def test_a_namespace_request_during_a_catalog_scan_makes_it_scan_once_more(scans: _Scans):
    """The namespace scan runs, and the catalog scan that read the policies before it scans exactly once more."""
    scans.hold_first_catalog_sync.set()
    scans.gateway.send(SendDiscoveryRequestGatewayInput(CATALOG, None))
    scans.wait_until(lambda: scans.catalog_syncs() == 1, "the catalog scan's first sync")

    scans.gateway.send(SendDiscoveryRequestGatewayInput(CATALOG, "sales", change_id="c1"))
    scans.wait_until(lambda: {"catalog": CATALOG, "namespace": "sales"} in scans.synced, "the namespace scan")
    scans.hold_first_catalog_sync.clear()

    async def catalog_result() -> Any:  # noqa: ANN401
        return await scans.client.get_workflow_handle(CATALOG_SCAN).result()

    scans.bridge.run(catalog_result, timeout=30)
    assert scans.catalog_syncs() == 2
    namespace_scan = table_discovery_adhoc_workflow_id(CATALOG, "sales", change_id="c1")
    scans.wait_until(lambda: len(scans.runs(CATALOG_SCAN)) == 2, "the catalog scan's second run")
    assert scans.runs(namespace_scan) == [WorkflowExecutionStatus.COMPLETED]


def test_a_namespace_request_with_no_catalog_scan_running_starts_none(scans: _Scans):
    """With no catalog scan going, a namespace request succeeds and starts only the namespace scan."""
    scans.gateway.send(SendDiscoveryRequestGatewayInput(CATALOG, "sales", change_id="c1"))

    scans.wait_until(lambda: {"catalog": CATALOG, "namespace": "sales"} in scans.synced, "the namespace scan")
    time.sleep(0.5)
    assert scans.catalog_syncs() == 0
    assert scans.runs(CATALOG_SCAN) == []


def test_a_namespace_request_after_the_catalog_scan_finished_starts_none(scans: _Scans):
    """A catalog scan that already completed is not restarted: the request succeeds and the scan has one run."""
    scans.gateway.send(SendDiscoveryRequestGatewayInput(CATALOG, None))

    async def catalog_result() -> Any:  # noqa: ANN401
        return await scans.client.get_workflow_handle(CATALOG_SCAN).result()

    scans.bridge.run(catalog_result, timeout=30)

    scans.gateway.send(SendDiscoveryRequestGatewayInput(CATALOG, "sales", change_id="c1"))

    scans.wait_until(lambda: {"catalog": CATALOG, "namespace": "sales"} in scans.synced, "the namespace scan")
    time.sleep(0.5)
    assert scans.catalog_syncs() == 1
    assert scans.runs(CATALOG_SCAN) == [WorkflowExecutionStatus.COMPLETED]
