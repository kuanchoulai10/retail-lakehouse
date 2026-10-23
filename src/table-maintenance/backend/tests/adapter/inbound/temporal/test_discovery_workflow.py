"""Test the DiscoveryWorkflow on a time-skipping Temporal test server."""

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

from adapter.inbound.temporal.workflows import DiscoveryWorkflow
from adapter.temporal_contracts.activity_names import SYNC_DISCOVERED_TABLES
from adapter.temporal_contracts.discovery_workflow_input import (
    DiscoveryWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import DISCOVERY_WORKFLOW


def _run_discovery(
    workflow_input: DiscoveryWorkflowInput, *, fail: bool = False
) -> tuple[Any, list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []

    @activity.defn(name=SYNC_DISCOVERED_TABLES)
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
                workflows=[DiscoveryWorkflow],
                activities=[sync_discovered_tables],
            ):
                return await asyncio.wait_for(
                    env.client.execute_workflow(
                        DISCOVERY_WORKFLOW,
                        workflow_input,
                        id=f"discovery-{uuid.uuid4()}",
                        task_queue=queue,
                    ),
                    timeout=20,
                )

    return asyncio.run(go()), requests


def test_discovery_syncs_catalog_and_returns_output():
    result, requests = _run_discovery(DiscoveryWorkflowInput("iceberg"))
    assert requests == [{"catalog": "iceberg", "namespace": None}]
    assert result == {"registered": 2, "dropped": 1}


def test_discovery_passes_namespace():
    _, requests = _run_discovery(DiscoveryWorkflowInput("iceberg", "sales.eu"))
    assert requests == [{"catalog": "iceberg", "namespace": "sales.eu"}]


def test_discovery_failure_fails_the_run():
    with pytest.raises(WorkflowFailureError):
        _run_discovery(DiscoveryWorkflowInput("iceberg"), fail=True)
