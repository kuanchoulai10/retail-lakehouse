"""Test the TableDiscoveryWorkflow on Temporal test servers: time-skipping for one scan, the dev server for rescans."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryActivity,
    TableDiscoverySignal,
    TableDiscoveryWorkflowInput,
    table_discovery_catalog_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableDiscoveryWorkflow,
)


def _run_discovery(
    workflow_input: TableDiscoveryWorkflowInput, *, fail: bool = False
) -> tuple[Any, list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []

    @activity.defn(name=TableDiscoveryActivity.SYNC_DISCOVERED_TABLES)
    async def sync_discovered_tables(request: dict[str, Any]) -> dict[str, Any]:
        requests.append(request)
        if fail:
            raise ApplicationError("catalog down", non_retryable=True)
        return {"registered": 2, "dropped": 1}

    async def go() -> Any:  # noqa: ANN401
        async with await WorkflowEnvironment.start_time_skipping() as env:
            queue = f"q-{uuid.uuid4()}"
            async with Worker(
                env.client,
                task_queue=queue,
                workflows=[TableDiscoveryWorkflow],
                activities=[sync_discovered_tables],
            ):
                return await asyncio.wait_for(
                    env.client.execute_workflow(
                        TABLE_DISCOVERY_WORKFLOW,
                        workflow_input,
                        id=f"discovery-{uuid.uuid4()}",
                        task_queue=queue,
                    ),
                    timeout=20,
                )

    return asyncio.run(go()), requests


def test_discovery_syncs_catalog_and_returns_output():
    """The workflow syncs the catalog without a namespace and returns the sync counts."""
    result, requests = _run_discovery(TableDiscoveryWorkflowInput("iceberg"))
    assert requests == [{"catalog": "iceberg", "namespace": None}]
    assert result == {"registered": 2, "dropped": 1}


def test_discovery_passes_namespace():
    """The workflow passes the namespace to the sync activity."""
    _, requests = _run_discovery(TableDiscoveryWorkflowInput("iceberg", "sales.eu"))
    assert requests == [{"catalog": "iceberg", "namespace": "sales.eu"}]


def test_discovery_failure_fails_the_run():
    """A failing sync activity fails the workflow run."""
    with pytest.raises(WorkflowFailureError):
        _run_discovery(TableDiscoveryWorkflowInput("iceberg"), fail=True)


def _scan_with_rescans(
    rescans_during_scan: int, *, signal_at_start: bool = False
) -> tuple[Any, list[dict[str, Any]], int]:
    """Run one catalog scan on a dev server, asking for ``rescans_during_scan`` rescans while its first sync runs.

    Return the result of the last run, every sync request and how many runs the workflow id had.
    """
    requests: list[dict[str, Any]] = []
    first_sync_started = asyncio.Event()
    release_first_sync = asyncio.Event()

    @activity.defn(name=TableDiscoveryActivity.SYNC_DISCOVERED_TABLES)
    async def sync_discovered_tables(request: dict[str, Any]) -> dict[str, Any]:
        requests.append(request)
        scan = len(requests)
        if scan == 1:
            first_sync_started.set()
            await release_first_sync.wait()
        return {"scan": scan}

    async def go() -> tuple[Any, int]:
        async with (
            await WorkflowEnvironment.start_local() as env,
            Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableDiscoveryWorkflow],
                activities=[sync_discovered_tables],
            ),
        ):
            workflow_id = table_discovery_catalog_workflow_id("iceberg")
            start: dict[str, Any] = {"start_signal": TableDiscoverySignal.REQUEST_RESCAN} if signal_at_start else {}
            handle = await env.client.start_workflow(
                TABLE_DISCOVERY_WORKFLOW,
                TableDiscoveryWorkflowInput("iceberg"),
                id=workflow_id,
                task_queue=TASK_QUEUE,
                **start,
            )
            await asyncio.wait_for(first_sync_started.wait(), timeout=20)
            for _ in range(rescans_during_scan):
                await handle.signal(TableDiscoverySignal.REQUEST_RESCAN)
            release_first_sync.set()
            result = await asyncio.wait_for(handle.result(), timeout=20)
            runs = [w async for w in env.client.list_workflows(f"WorkflowId = '{workflow_id}'")]
            return result, len(runs)

    result, runs = asyncio.run(go())
    return result, requests, runs


def test_a_rescan_requested_during_a_scan_runs_exactly_one_more_scan():
    """A rescan asked during a scan gives one more scan of the same scope, which syncs and reads the policies again."""
    result, requests, runs = _scan_with_rescans(1)

    assert requests == [{"catalog": "iceberg", "namespace": None}] * 2
    assert result == {"scan": 2}
    assert runs == 2


def test_no_rescan_request_means_no_second_scan():
    """A scan nobody asked to rescan runs once."""
    result, requests, runs = _scan_with_rescans(0)

    assert requests == [{"catalog": "iceberg", "namespace": None}]
    assert result == {"scan": 1}
    assert runs == 1


def test_two_rescan_requests_during_one_scan_run_only_one_more_scan():
    """Rescans asked for during one scan fold into one more scan."""
    result, requests, runs = _scan_with_rescans(2)

    assert len(requests) == 2
    assert result == {"scan": 2}
    assert runs == 2


def test_the_request_that_starts_a_scan_does_not_ask_for_a_second():
    """A signal-with-start that starts the scan is served by it: the pending flag is cleared as each run starts."""
    result, requests, runs = _scan_with_rescans(0, signal_at_start=True)

    assert len(requests) == 1
    assert result == {"scan": 1}
    assert runs == 1
