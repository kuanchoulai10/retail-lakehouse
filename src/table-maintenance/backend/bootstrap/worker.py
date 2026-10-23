"""Temporal worker entry point for the table-maintenance backend."""

from __future__ import annotations

import asyncio
import logging
import signal
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
from bootstrap.configs import get_settings
from bootstrap.container import (
    apply_worker_startup,
    build_activities,
    build_connected_use_cases,
    build_worker,
    configure_logging,
    connect_temporal,
)

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings

logger = logging.getLogger(__name__)

ACTIVITY_THREADS = 16


async def run_worker(settings: AppSettings) -> None:
    """Run the worker until SIGTERM or SIGINT, then shut it down gracefully.

    Two Temporal clients exist: the gateways' client lives on the bridge loop, the
    worker's own client (worker, schedules, signal activities) on this loop.
    """
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    bridge = AsyncLoopBridge()
    try:
        use_cases = await asyncio.to_thread(build_connected_use_cases, settings, bridge)
        client = await connect_temporal(settings.temporal)
        await apply_worker_startup(client, settings, use_cases.get_discovery_settings)
        activities = build_activities(use_cases, client, settings)
        with ThreadPoolExecutor(
            max_workers=ACTIVITY_THREADS, thread_name_prefix="activity"
        ) as executor:
            worker = build_worker(
                client,
                activities,
                settings.temporal,
                executor=executor,
                max_concurrent_activities=ACTIVITY_THREADS,
            )
            async with worker:
                logger.info("worker polling %s", settings.temporal.task_queue)
                await stop.wait()
                logger.info("stop requested; shutting the worker down")
    finally:
        await asyncio.to_thread(bridge.close)


def main() -> None:
    """Run the Temporal worker component."""
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(run_worker(settings))
