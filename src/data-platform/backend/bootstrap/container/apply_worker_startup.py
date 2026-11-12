"""Provide the apply_worker_startup function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from bootstrap.container.admission_lease_seconds import admission_lease_seconds
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
    ensure_table_maintenance_admission,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client

    from bootstrap.configs import AppSettings


async def apply_worker_startup(
    client: Client,
    settings: AppSettings,
    *,
    ensure_schedule: Callable[..., Awaitable[None]] = ensure_table_discovery_schedule,
    ensure_admission: Callable[..., Awaitable[None]] = ensure_table_maintenance_admission,
) -> None:
    """Ensure the per-catalog discovery schedules and the admission workflow.

    The discovery schedules always run: the discovery rules alone decide which
    tables are managed, so there is no switch to pause them.
    """
    await ensure_schedule(
        client,
        list(settings.catalog.names),
        interval=timedelta(seconds=settings.discovery_interval_seconds),
    )
    await ensure_admission(
        client,
        limit=settings.admission_limit,
        lease_seconds=admission_lease_seconds(settings),
    )
