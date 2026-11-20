"""Provide the apply_worker_startup function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
    require_table_search_attributes,
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
    require_attributes: Callable[..., Awaitable[None]] = require_table_search_attributes,
) -> None:
    """Ensure the per-catalog discovery schedules.

    It first checks that the namespace has every search attribute the
    workflows set, and fails the start otherwise (``MissingTableSearchAttributes``
    names them and says to run ``platform/21-temporal/bootstrap.sh``): without
    them every workflow that tags itself would fail its workflow task. The
    discovery schedules always run: the discovery rules alone decide which
    tables are managed, so there is no switch to pause them.
    """
    await require_attributes(client)
    await ensure_schedule(
        client,
        list(settings.catalog.names),
        interval=timedelta(seconds=settings.discovery_interval_seconds),
    )
