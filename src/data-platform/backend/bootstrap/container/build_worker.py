"""Provide the build_worker function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio.worker import Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableDiscoveryWorkflow,
    TableMaintenanceAdmissionWorkflow,
    TableMaintenanceWorkflow,
    TableReconciliationWorkflow,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from concurrent.futures import ThreadPoolExecutor

    from temporalio.client import Client

    from bootstrap.container.activities import Activities

WORKFLOWS = (
    TableReconciliationWorkflow,
    TableDiscoveryWorkflow,
    TableMaintenanceWorkflow,
    TableMaintenanceAdmissionWorkflow,
)
GRACEFUL_SHUTDOWN = timedelta(seconds=30)


def build_worker(
    client: Client,
    activities: Activities,
    *,
    executor: ThreadPoolExecutor,
    max_concurrent_activities: int,
    worker_factory: Callable[..., Worker] = Worker,
) -> Worker:
    """Build the worker that runs all four workflows and every activity.

    Sync activities run on ``executor``; ``max_concurrent_activities`` should match
    its thread count so an accepted task never waits for a free thread.
    """
    return worker_factory(
        client,
        task_queue=TASK_QUEUE,
        workflows=list(WORKFLOWS),
        activities=activities.callables(),
        activity_executor=executor,
        max_concurrent_activities=max_concurrent_activities,
        graceful_shutdown_timeout=GRACEFUL_SHUTDOWN,
    )
