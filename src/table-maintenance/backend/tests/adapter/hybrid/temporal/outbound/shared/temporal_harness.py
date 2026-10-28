"""Provide a local Temporal dev server, a worker with stub workflows and a bridge."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from temporalio import workflow
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
from adapter.hybrid.temporal.contracts import (
    TABLE_DISCOVERY_WORKFLOW,
    TABLE_MAINTENANCE_WORKFLOW,
    TABLE_RECONCILIATION_WORKFLOW,
    TASK_QUEUE,
)


@workflow.defn(name=TABLE_RECONCILIATION_WORKFLOW)
class StubTableReconciliationWorkflow:
    def __init__(self) -> None:
        self.received: list[tuple[str, dict]] = []

    @workflow.run
    async def run(self, input: dict) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name="settings_changed")
    def settings_changed(self, payload: dict) -> None:
        self.received.append(("settings_changed", payload))

    @workflow.signal(name="table_updated")
    def table_updated(self, payload: dict) -> None:
        self.received.append(("table_updated", payload))

    @workflow.signal(name="pause")
    def pause(self, payload: dict) -> None:
        self.received.append(("pause", payload))

    @workflow.signal(name="resume")
    def resume(self, payload: dict) -> None:
        self.received.append(("resume", payload))

    @workflow.signal(name="stop")
    def stop(self, payload: dict) -> None:
        self.received.append(("stop", payload))

    @workflow.signal(name="trigger_now")
    def trigger_now(self, payload: dict) -> None:
        self.received.append(("trigger_now", payload))

    @workflow.query
    def signals(self) -> list[tuple[str, dict]]:
        return self.received


@workflow.defn(name=TABLE_MAINTENANCE_WORKFLOW)
class StubTableMaintenanceWorkflow:
    def __init__(self) -> None:
        self.results: list[dict] = []

    @workflow.run
    async def run(self, input: dict) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name="operation_result")
    def operation_result(self, result: dict) -> None:
        self.results.append(result)

    @workflow.query
    def collected(self) -> list[dict]:
        return self.results


@workflow.defn(name=TABLE_DISCOVERY_WORKFLOW)
class StubTableDiscoveryWorkflow:
    @workflow.run
    async def run(self, input: dict) -> None:
        await workflow.wait_condition(lambda: False)


@dataclass
class TemporalHarness:
    client: Client
    bridge: AsyncLoopBridge


@pytest.fixture(scope="session")
def harness() -> Iterator[TemporalHarness]:
    bridge = AsyncLoopBridge()
    env = bridge.run(lambda: WorkflowEnvironment.start_local(), timeout=300)
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
