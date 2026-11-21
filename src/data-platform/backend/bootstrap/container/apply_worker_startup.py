"""Provide the apply_worker_startup function."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    require_table_search_attributes,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesUseCaseInput,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client

    from bootstrap.container.use_cases import UseCases

logger = logging.getLogger(__name__)


async def apply_worker_startup(
    client: Client,
    use_cases: UseCases,
    *,
    require_attributes: Callable[..., Awaitable[None]] = require_table_search_attributes,
) -> None:
    """Check the search attributes, then bring the discovery schedules in line with the scanned catalogs.

    The check fails the start when the namespace lacks a search attribute the workflows set
    (``MissingTableSearchAttributes`` names them and says to run ``platform/21-temporal/bootstrap.sh``):
    without them every workflow that tags itself would fail its workflow task. The schedule sync is a
    full reconcile, and any failure of it fails the start, loudly. It runs in a thread, so its gateways,
    which block until the bridge loop answers, do not stall this event loop.
    """
    await require_attributes(client)
    out = await asyncio.to_thread(use_cases.sync_discovery_schedules.execute, SyncDiscoverySchedulesUseCaseInput())
    logger.info("discovery schedules synced for the scanned catalogs %s", list(out.catalogs))
