"""Test building the use cases with a Temporal client connected on the bridge loop."""

from __future__ import annotations

import threading
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bootstrap.container import (
    build_connected_use_cases,
    build_engine,
    build_operation_cooldowns,
    build_partition_selection_settings,
    build_size_memory,
    run_migrations,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.adapter.outbound.table.sql import TableMetricsSqlStore
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import GetPlatformSettingsUseCaseInput
from context.table_maintenance.application.service.table import PlanTableMaintenanceService
from context.table_maintenance.application.service.table_maintenance_run import (
    RecordTableMaintenanceOperationResultService,
)
from tests.bootstrap.container.container_support import sqlite_settings

if TYPE_CHECKING:
    from bootstrap.configs import TemporalSettings


def test_connects_the_gateway_client_on_the_bridge_loop(tmp_path):
    """The Temporal client is connected on the async loop bridge and the use cases work."""
    settings = sqlite_settings()
    settings.database.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings.database))
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
    settings.database.sqlite.path = str(tmp_path / "tm.db")

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


def test_the_planner_reads_the_cooldowns_the_settings_say(tmp_path):
    """The planner reads the cooldowns and the backoff cap the worker and the api are given."""
    settings = sqlite_settings(
        maintenance={"failure_backoff_cap_seconds": 7200, "rewrite_data_files_cooldown_seconds": 60}
    )
    settings.database.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    planner = use_cases.plan_table_maintenance
    assert isinstance(planner, PlanTableMaintenanceService)
    expected = build_operation_cooldowns(settings.maintenance)
    assert expected.failure_backoff_cap == timedelta(hours=2)
    assert expected.rewrite_data_files == timedelta(seconds=60)
    assert planner._cooldowns == expected  # noqa: SLF001


def test_the_planner_reads_the_partition_selection_the_settings_say(tmp_path):
    """The planner reads the partition selection the worker and the api are given."""
    settings = sqlite_settings(maintenance={"compaction_quiet_seconds": 0})
    settings.database.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    planner = use_cases.plan_table_maintenance
    assert isinstance(planner, PlanTableMaintenanceService)
    expected = build_partition_selection_settings(settings.maintenance)
    assert expected.quiet_period == timedelta(0)
    assert planner._partition_selection == expected  # noqa: SLF001


def test_the_planner_saves_the_metrics_in_sql(tmp_path):
    """The built plan service keeps the table metrics in the SQL store."""
    settings = sqlite_settings()
    settings.database.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    planner = use_cases.plan_table_maintenance
    assert isinstance(planner, PlanTableMaintenanceService)
    assert isinstance(planner._metrics_store, TableMetricsSqlStore)  # noqa: SLF001


def test_the_platform_settings_page_reads_the_settings_the_components_run_on(tmp_path):
    """The listed platform settings are the ones the same settings give the worker's and the api's services."""
    settings = sqlite_settings(maintenance={"max_attempts": 4, "failure_backoff_cap_seconds": 7200})
    settings.database.sqlite.path = str(tmp_path / "tm.db")

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
