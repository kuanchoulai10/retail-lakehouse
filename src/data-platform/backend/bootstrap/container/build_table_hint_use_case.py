"""Provide the build_table_hint_use_case function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bootstrap.container.build_catalog_factory import build_catalog_factory
from bootstrap.container.build_engine import build_engine
from bootstrap.container.build_repositories import build_repositories
from bootstrap.container.connect_temporal import connect_temporal
from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
    SendTableChangeTemporalGateway,
)
from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    ReadTableMetadataPyIcebergGateway,
)
from context.table_maintenance.application.service.table import ProcessTableHintService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client

    from bootstrap.configs import EventConsumerSettings, TemporalSettings
    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )
    from context.table_maintenance.application.port.inbound.table import ProcessTableHintUseCase


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_table_hint_use_case(
    settings: EventConsumerSettings,
    bridge: AsyncLoopBridge,
    *,
    connect: Callable[[TemporalSettings], Awaitable[Client]] = connect_temporal,
) -> ProcessTableHintUseCase:
    """Build the one use case the event consumer runs, on its database, catalog and Temporal only.

    The Temporal client is connected on ``bridge``'s loop, since the gateways run every call there.
    """
    client = bridge.run(lambda: connect(settings.temporal))
    repositories = build_repositories(build_engine(settings.database))
    return ProcessTableHintService(
        repositories.tables,
        repositories.table_discovery_policies,
        repositories.table_discovery_policy_attachments,
        ReadTableMetadataPyIcebergGateway(build_catalog_factory(settings.catalog)),
        SendTableChangeTemporalGateway(client, bridge),
        SendDiscoveryRequestTemporalGateway(client, bridge),
        clock=_utc_now,
    )
