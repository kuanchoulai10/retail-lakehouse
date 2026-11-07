"""Test building the use cases with a Temporal client connected on the bridge loop."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bootstrap.container import build_connected_use_cases, build_engine, run_migrations
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    ListTableMaintenancePresetsUseCaseInput,
)
from tests.bootstrap.container.container_support import sqlite_settings

if TYPE_CHECKING:
    from bootstrap.configs import TemporalSettings


def test_connects_the_gateway_client_on_the_bridge_loop(tmp_path):
    """The Temporal client is connected on the async loop bridge and the use cases work."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings))
    connected: list[tuple[str, str]] = []
    client = MagicMock(name="client")

    async def connect(temporal: TemporalSettings):
        connected.append((temporal.address, threading.current_thread().name))
        return client

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(
            settings,
            bridge,
            connect=connect,
            k8s_api_factory=MagicMock,
        )
        listing = use_cases.list_table_maintenance_presets.execute(ListTableMaintenancePresetsUseCaseInput())
    finally:
        bridge.close()

    assert connected == [(settings.temporal.address, "async-loop-bridge")]
    assert [item.name for item in listing.items] == ["default"]
