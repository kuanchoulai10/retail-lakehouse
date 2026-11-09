"""Provide a local Temporal dev server, a worker with stub workflows and a bridge."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from temporalio import workflow
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from temporalio.client import Client


@workflow.defn(name=TABLE_RECONCILIATION_WORKFLOW)
class StubTableReconciliationWorkflow:
    """Reconciliation workflow stub that records the signals it receives."""

    def __init__(self) -> None:
        """Start with no received signals."""
        self.received: list[tuple[str, dict]] = []

    @workflow.run
    async def run(self, payload: dict) -> None:
        """Wait forever so signals can be collected."""
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name="settings_changed")
    def settings_changed(self, payload: dict) -> None:
        """Record a settings_changed signal."""
        self.received.append(("settings_changed", payload))

    @workflow.signal(name="table_updated")
    def table_updated(self, payload: dict) -> None:
        """Record a table_updated signal."""
        self.received.append(("table_updated", payload))

    @workflow.signal(name="table_seen")
    def table_seen(self, payload: dict) -> None:
        """Record a table_seen signal."""
        self.received.append(("table_seen", payload))

    @workflow.signal(name="pause")
    def pause(self, payload: dict) -> None:
        """Record a pause signal."""
        self.received.append(("pause", payload))

    @workflow.signal(name="resume")
    def resume(self, payload: dict) -> None:
        """Record a resume signal."""
        self.received.append(("resume", payload))

    @workflow.signal(name="stop")
    def stop(self, payload: dict) -> None:
        """Record a stop signal."""
        self.received.append(("stop", payload))

    @workflow.signal(name="trigger_now")
    def trigger_now(self, payload: dict) -> None:
        """Record a trigger_now signal."""
        self.received.append(("trigger_now", payload))

    @workflow.signal(name="reconcile_now")
    def reconcile_now(self, payload: dict) -> None:
        """Record a reconcile_now signal."""
        self.received.append(("reconcile_now", payload))

    @workflow.query
    def signals(self) -> list[tuple[str, dict]]:
        """Query returning the received signals."""
        return self.received


@workflow.defn(name=TABLE_MAINTENANCE_WORKFLOW)
class StubTableMaintenanceWorkflow:
    """Maintenance workflow stub that collects the operation results signalled to it."""

    def __init__(self) -> None:
        """Start with no collected results."""
        self.results: list[dict] = []

    @workflow.run
    async def run(self, payload: dict) -> None:
        """Wait forever so results can be collected."""
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name="operation_result")
    def operation_result(self, result: dict) -> None:
        """Collect an operation result signal."""
        self.results.append(result)

    @workflow.query
    def collected(self) -> list[dict]:
        """Query returning the collected results."""
        return self.results


@workflow.defn(name=TABLE_DISCOVERY_WORKFLOW)
class StubTableDiscoveryWorkflow:
    """Discovery workflow stub that waits forever."""

    @workflow.run
    async def run(self, payload: dict) -> None:
        """Wait forever."""
        await workflow.wait_condition(lambda: False)


@dataclass
class TemporalHarness:
    """A running Temporal test environment with its client and loop bridge."""

    client: Client
    bridge: AsyncLoopBridge


@pytest.fixture(scope="session")
def harness() -> Iterator[TemporalHarness]:
    """Provide a session-wide local Temporal environment with the stub workflows registered."""
    bridge = AsyncLoopBridge()
    env = bridge.run(WorkflowEnvironment.start_local, timeout=300)
    worker = Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflow_runner=UnsandboxedWorkflowRunner(),
        workflows=[
            StubTableReconciliationWorkflow,
            StubTableMaintenanceWorkflow,
            StubTableDiscoveryWorkflow,
        ],
    )

    run_tasks: list[asyncio.Task] = []

    async def start_worker() -> None:
        run_tasks.append(asyncio.ensure_future(worker.run()))

    bridge.run(start_worker)
    try:
        yield TemporalHarness(client=env.client, bridge=bridge)
    finally:

        async def stop() -> None:
            await worker.shutdown()
            await asyncio.gather(*run_tasks)
            await env.shutdown()

        bridge.run(stop, timeout=60)
        bridge.close()
