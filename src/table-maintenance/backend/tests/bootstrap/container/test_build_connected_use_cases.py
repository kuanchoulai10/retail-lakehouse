from __future__ import annotations

import threading
from unittest.mock import MagicMock

from adapter.hybrid.temporal.outbound.shared.async_loop_bridge import AsyncLoopBridge
from application.port.inbound.table_maintenance_preset.list_table_maintenance_presets import (
    ListTableMaintenancePresetsUseCaseInput,
)
from bootstrap.configs import TemporalSettings
from bootstrap.container import build_connected_use_cases, run_migrations
from bootstrap.container import build_engine
from tests.bootstrap.container.container_support import sqlite_settings


def test_connects_the_gateway_client_on_the_bridge_loop(tmp_path):
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
        listing = use_cases.list_table_maintenance_presets.execute(
            ListTableMaintenancePresetsUseCaseInput()
        )
    finally:
        bridge.close()

    assert connected == [(settings.temporal.address, "async-loop-bridge")]
    assert [item.name for item in listing.items] == ["default"]
