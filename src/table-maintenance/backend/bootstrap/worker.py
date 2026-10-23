"""Temporal worker entry point for the table-maintenance backend."""

from __future__ import annotations

import asyncio
import logging
import signal
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
from application.domain.model.maintenance.workflow_ids import TASK_QUEUE
from bootstrap.configs import get_settings
from bootstrap.container import (
    apply_worker_startup,
    build_activities,
    build_connected_use_cases,
    build_k8s_api,
    build_worker,
    configure_logging,
    connect_temporal,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from kubernetes.client import CustomObjectsApi
    from temporalio.client import Client
    from temporalio.worker import Worker

    from bootstrap.configs import AppSettings, TemporalSettings
    from bootstrap.container.use_cases import UseCases

logger = logging.getLogger(__name__)

ACTIVITY_THREADS = 16


def install_signal_stop(callback: Callable[[], None]) -> None:
    """Call ``callback`` on SIGTERM or SIGINT, from the running event loop."""
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, callback)


async def run_worker(  # noqa: PLR0913
    settings: AppSettings,
    *,
    bridge_factory: Callable[[], AsyncLoopBridge] = AsyncLoopBridge,
    use_cases_builder: Callable[..., UseCases] = build_connected_use_cases,
    k8s_api_factory: Callable[[], CustomObjectsApi] = build_k8s_api,
    connect: Callable[[TemporalSettings], Awaitable[Client]] = connect_temporal,
    startup: Callable[..., Awaitable[None]] = apply_worker_startup,
    worker_builder: Callable[..., Worker] = build_worker,
    install_stop: Callable[[Callable[[], None]], None] = install_signal_stop,
) -> None:
    """Run the worker until a stop request, then shut it down gracefully.

    Two Temporal clients exist: the gateways' client lives on the bridge loop, the
    worker's own client (worker, schedules, signal activities) on this loop. The
    Kubernetes client is built up front so a worker without cluster access fails
    at start rather than on its first Spark submit.
    """
    stop = asyncio.Event()
    install_stop(stop.set)
    bridge = bridge_factory()
    try:
        k8s_api = await asyncio.to_thread(k8s_api_factory)
        use_cases = await asyncio.to_thread(
            use_cases_builder, settings, bridge, k8s_api_factory=lambda: k8s_api
        )
        client = await connect(settings.temporal)
        await startup(client, settings, use_cases.get_discovery_settings)
        activities = build_activities(use_cases, client, settings)
        with ThreadPoolExecutor(
            max_workers=ACTIVITY_THREADS, thread_name_prefix="activity"
        ) as executor:
            worker = worker_builder(
                client,
                activities,
                executor=executor,
                max_concurrent_activities=ACTIVITY_THREADS,
            )
            async with worker:
                logger.info("worker polling %s", TASK_QUEUE)
                await stop.wait()
                logger.info("stop requested; shutting the worker down")
    finally:
        await asyncio.to_thread(bridge.close)


def main() -> None:
    """Run the Temporal worker component."""
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(run_worker(settings))
