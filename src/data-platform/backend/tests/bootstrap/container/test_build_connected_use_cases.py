"""Test building the use cases with a Temporal client connected on the bridge loop."""

from __future__ import annotations

import threading
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bootstrap.container import (
    build_connected_use_cases,
    build_engine,
    build_size_memory,
    run_migrations,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import GetPlatformSettingsUseCaseInput
from context.table_maintenance.application.service.table import GetTableHealthService, PlanTableMaintenanceService
from context.table_maintenance.application.service.table_maintenance_run import (
    RecordTableMaintenanceOperationResultService,
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
        listing = use_cases.list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput())
    finally:
        bridge.close()

    assert connected == [(settings.temporal.address, "async-loop-bridge")]
    assert [item.name for item in listing.items] == ["default"]


def test_the_recorder_knows_each_size_s_memory(tmp_path):
    """The operation result recorder is given each size's memory, so it can step a table down."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    recorder = use_cases.record_table_maintenance_operation_result
    assert isinstance(recorder, RecordTableMaintenanceOperationResultService)
    assert recorder._size_memory == build_size_memory(settings.spark)  # noqa: SLF001


def test_the_planner_and_the_health_report_cap_the_failure_backoff_as_the_settings_say(tmp_path):
    """Both the planner and the table health read the failure backoff cap the worker and the api are given."""
    settings = sqlite_settings(maintenance_failure_backoff_cap_seconds=7200)
    settings.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    planner = use_cases.plan_table_maintenance
    health = use_cases.get_table_health
    assert isinstance(planner, PlanTableMaintenanceService)
    assert isinstance(health, GetTableHealthService)
    assert planner._failure_backoff_cap == timedelta(hours=2)  # noqa: SLF001
    assert health._failure_backoff_cap == timedelta(hours=2)  # noqa: SLF001


def test_the_platform_settings_page_reads_the_settings_the_components_run_on(tmp_path):
    """The listed platform settings are the ones the same settings give the worker's and the api's services."""
    settings = sqlite_settings(maintenance_max_attempts=4, maintenance_failure_backoff_cap_seconds=7200)
    settings.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    output = use_cases.get_platform_settings.execute(GetPlatformSettingsUseCaseInput())
    values = {item.key: item.value for group in output.groups for item in group.items}
    assert values["maintenance_max_attempts"] == 4
    assert values["maintenance_failure_backoff_cap_seconds"] == 7200
