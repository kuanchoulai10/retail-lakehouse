"""Test the TableDiscoveryWorkflow on a time-skipping Temporal test server."""

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

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryActivity,
    TableDiscoveryWorkflowInput,
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
