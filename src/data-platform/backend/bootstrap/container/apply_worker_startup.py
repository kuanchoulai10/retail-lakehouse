"""Provide the apply_worker_startup function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
    require_table_search_attributes,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import timedelta

    from temporalio.client import Client

    from bootstrap.container.use_cases import UseCases

logger = logging.getLogger(__name__)


async def apply_worker_startup(
    client: Client,
    use_cases: UseCases,  # noqa: ARG001
    *,
    interval: timedelta,
    require_attributes: Callable[..., Awaitable[None]] = require_table_search_attributes,
) -> None:
    """Check the search attributes, then ensure the one discovery schedule at ``interval``.

    The check fails the start when the namespace lacks a search attribute the workflows set
    (``MissingTableSearchAttributes`` names them and says to run ``platform/21-temporal/bootstrap.sh``):
    without them every workflow that tags itself would fail its workflow task. The schedule starts a
    discovery round every ``interval``, and the round reads the catalogs to scan each time, so nothing
    here depends on which catalogs are scanned. Any failure of either step fails the start, loudly.
    """
    await require_attributes(client)
    await ensure_table_discovery_schedule(client, interval=interval)
    logger.info("discovery schedule ensured, every %s", interval)
