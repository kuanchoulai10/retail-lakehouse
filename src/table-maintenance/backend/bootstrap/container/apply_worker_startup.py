"""Provide the apply_worker_startup function."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

from adapter.inbound.temporal.ensure_capacity_limiter import ensure_capacity_limiter
from adapter.inbound.temporal.ensure_discovery_schedule import (
    ensure_discovery_schedule,
)
from application.port.inbound.discovery.get_discovery_settings import (
    GetDiscoverySettingsUseCaseInput,
)
from bootstrap.container.capacity_lease_seconds import CAPACITY_LEASE_SECONDS

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client

    from application.port.inbound.discovery.get_discovery_settings import (
        GetDiscoverySettingsUseCase,
    )
    from bootstrap.configs.app_settings import AppSettings


async def apply_worker_startup(
    client: Client,
    settings: AppSettings,
    get_discovery_settings: GetDiscoverySettingsUseCase,
    *,
    ensure_schedule: Callable[..., Awaitable[None]] = ensure_discovery_schedule,
    ensure_limiter: Callable[..., Awaitable[None]] = ensure_capacity_limiter,
) -> None:
    """Bring the discovery schedules and the capacity limiter in line with the DB.

    The discovery switch comes from the DB (an absent row means enabled), so every
    worker start re-applies it to the per-catalog schedules.
    """
    discovery = await asyncio.to_thread(
        get_discovery_settings.execute, GetDiscoverySettingsUseCaseInput()
    )
    await ensure_schedule(
        client,
        list(settings.catalog.names),
        paused=not discovery.enabled,
        interval=timedelta(seconds=settings.discovery_interval_seconds),
    )
    await ensure_limiter(
        client,
        limit=settings.capacity_limit,
        lease_seconds=CAPACITY_LEASE_SECONDS,
        task_queue=settings.temporal.task_queue,
    )
