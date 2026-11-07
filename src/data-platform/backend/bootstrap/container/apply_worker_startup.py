"""Provide the apply_worker_startup function."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

from bootstrap.container.admission_lease_seconds import ADMISSION_LEASE_SECONDS
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
    ensure_table_maintenance_admission,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings import (
    GetTableDiscoverySettingsUseCaseInput,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client

    from bootstrap.configs import AppSettings
    from context.table_maintenance.application.port.inbound.table_discovery_settings import (
        GetTableDiscoverySettingsUseCase,
    )


async def apply_worker_startup(
    client: Client,
    settings: AppSettings,
    get_table_discovery_settings: GetTableDiscoverySettingsUseCase,
    *,
    ensure_schedule: Callable[..., Awaitable[None]] = ensure_table_discovery_schedule,
    ensure_admission: Callable[..., Awaitable[None]] = ensure_table_maintenance_admission,
) -> None:
    """Bring the discovery schedules and the admission workflow in line with the DB.

    The discovery switch comes from the DB (an absent row means enabled), so every
    worker start re-applies it to the per-catalog schedules.
    """
    discovery = await asyncio.to_thread(get_table_discovery_settings.execute, GetTableDiscoverySettingsUseCaseInput())
    await ensure_schedule(
        client,
        list(settings.catalog.names),
        paused=not discovery.enabled,
        interval=timedelta(seconds=settings.discovery_interval_seconds),
    )
    await ensure_admission(
        client,
        limit=settings.admission_limit,
        lease_seconds=ADMISSION_LEASE_SECONDS,
    )
