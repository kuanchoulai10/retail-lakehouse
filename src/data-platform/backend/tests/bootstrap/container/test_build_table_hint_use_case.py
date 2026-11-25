"""Test that the event consumer's wiring builds the table hint use case from its own settings only."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bootstrap.container import build_table_hint_use_case
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.application.service.table import ProcessTableHintService
from tests.bootstrap.container.container_support import sqlite_event_consumer_settings

if TYPE_CHECKING:
    from bootstrap.configs import TemporalSettings


def test_build_table_hint_use_case_needs_no_spark_settings():
    """The event consumer's settings, which hold no Spark, maintenance or metrics, build the use case."""
    connected: list[str] = []

    async def connect(temporal: TemporalSettings):
        connected.append(temporal.address)
        return MagicMock(name="client")

    settings = sqlite_event_consumer_settings(temporal={"address": "temporal:7233"})
    bridge = AsyncLoopBridge()
    try:
        use_case = build_table_hint_use_case(settings, bridge, connect=connect)
    finally:
        bridge.close()

    assert isinstance(use_case, ProcessTableHintService)
    assert connected == ["temporal:7233"]
