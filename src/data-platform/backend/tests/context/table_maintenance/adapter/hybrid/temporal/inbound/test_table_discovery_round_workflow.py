"""Test the TableDiscoveryRoundWorkflow on a local Temporal dev server.

The dev server, not the time-skipping one, since only it applies a parent close policy: skipping
time would also run the abandoned scans' clocks out.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

import pytest
from temporalio import activity
from temporalio.api.enums.v1 import WorkflowExecutionStatus
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
    table_discovery_catalog_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TABLE_DISCOVERY_ROUND_WORKFLOW,
    TableDiscoveryRoundActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableDiscoveryRoundWorkflow,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_discovery_stub_workflow import (
    FAILING_CATALOG,
    TableDiscoveryStubWorkflow,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client


def _with_round(catalogs: list[str], body: Callable[[Client], Awaitable[Any]]) -> Any:  # noqa: ANN401
    """Run ``body`` against a worker running the round, whose listing returns ``catalogs``, and stub scans."""

    @activity.defn(name=TableDiscoveryRoundActivity.LIST_SCANNED_CATALOGS)
    async def list_scanned_catalogs() -> list[str]:
        return catalogs

    async def go() -> Any:  # noqa: ANN401
        async with (
            await WorkflowEnvironment.start_local() as env,
            Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableDiscoveryRoundWorkflow, TableDiscoveryStubWorkflow],
                activities=[list_scanned_catalogs],
            ),
        ):
            return await asyncio.wait_for(body(env.client), timeout=30)

    return asyncio.run(go())


async def _run_round(client: Client) -> dict[str, Any]:
    return await client.execute_workflow(
        TABLE_DISCOVERY_ROUND_WORKFLOW, id=f"round-{uuid.uuid4()}", task_queue=TASK_QUEUE
    )


async def _status(client: Client, workflow_id: str) -> WorkflowExecutionStatus.ValueType:
    description = await client.get_workflow_handle(workflow_id).describe()
    return description.raw_description.workflow_execution_info.status


def test_one_child_scan_per_catalog():
    """Each scanned catalog gets one scan, under its catalog scan id, scoped to the whole catalog."""

    async def body(client: Client) -> tuple[dict[str, Any], list[Any]]:
        result = await _run_round(client)
        scans = []
        for catalog in ("a", "b"):
            handle = client.get_workflow_handle(table_discovery_catalog_workflow_id(catalog))
            await handle.signal("finish")
            scans.append(await handle.result())
        return result, scans

    result, scans = _with_round(["a", "b"], body)

    assert result == {"started": ["a", "b"], "already_running": []}
    assert scans == [{"catalog": "a", "namespace": None}, {"catalog": "b", "namespace": None}]


def test_a_catalog_already_being_scanned_is_skipped():
    """A catalog whose scan is still going is reported already running, and the next catalog still starts."""

    async def body(client: Client) -> tuple[dict[str, Any], str]:
        running = await client.start_workflow(
            TABLE_DISCOVERY_WORKFLOW,
            TableDiscoveryWorkflowInput("a"),
            id=table_discovery_catalog_workflow_id("a"),
            task_queue=TASK_QUEUE,
        )
        result = await _run_round(client)
        description = await client.get_workflow_handle(table_discovery_catalog_workflow_id("a")).describe()
        b_status = await _status(client, table_discovery_catalog_workflow_id("b"))
        assert description.run_id == running.result_run_id
        return result, WorkflowExecutionStatus.Name(b_status)

    result, b_status = _with_round(["a", "b"], body)

    assert result == {"started": ["b"], "already_running": ["a"]}
    assert b_status == "WORKFLOW_EXECUTION_STATUS_RUNNING"


def test_the_round_does_not_wait_for_its_children():
    """The round completes while the scan it started is still running, and closing it leaves the scan running."""

    async def body(client: Client) -> tuple[dict[str, Any], str, Any]:
        result = await _run_round(client)
        scan = client.get_workflow_handle(table_discovery_catalog_workflow_id("a"))
        await asyncio.sleep(1)
        status = await _status(client, scan.id)
        await scan.signal("finish")
        return result, WorkflowExecutionStatus.Name(status), await scan.result()

    result, status, scanned = _with_round(["a"], body)

    assert result == {"started": ["a"], "already_running": []}
    assert status == "WORKFLOW_EXECUTION_STATUS_RUNNING"
    assert scanned == {"catalog": "a", "namespace": None}


def test_a_failing_scan_does_not_stop_the_others():
    """A scan that fails at once neither fails the round nor stops the next catalog's scan from completing."""

    async def body(client: Client) -> tuple[dict[str, Any], Any]:
        result = await _run_round(client)
        failing = client.get_workflow_handle(table_discovery_catalog_workflow_id(FAILING_CATALOG))
        with pytest.raises(WorkflowFailureError):
            await failing.result()
        other = client.get_workflow_handle(table_discovery_catalog_workflow_id("b"))
        await other.signal("finish")
        return result, await other.result()

    result, other = _with_round([FAILING_CATALOG, "b"], body)

    assert result == {"started": [FAILING_CATALOG, "b"], "already_running": []}
    assert other == {"catalog": "b", "namespace": None}


def test_a_round_with_no_scanned_catalog_starts_nothing():
    """With no catalog to scan the round starts no scan."""
    assert _with_round([], _run_round) == {"started": [], "already_running": []}
