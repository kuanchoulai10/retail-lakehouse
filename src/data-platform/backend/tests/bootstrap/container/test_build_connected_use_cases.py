"""Test building the use cases with a Temporal client connected on the bridge loop."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bootstrap.container import (
    build_candidate_selection,
    build_connected_use_cases,
    build_engine,
    build_size_memory,
    compaction_claim_lease,
    run_migrations,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePoliciesUseCaseInput,
)
from context.table_maintenance.application.service.compaction_candidate import ListCompactionCandidatesService
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


def test_the_planner_knows_each_size_s_memory_and_the_claim_lease(tmp_path):
    """The planner estimates costs with each size's memory and claims candidates for the worker's lease."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    planner = use_cases.plan_table_maintenance
    assert isinstance(planner, PlanTableMaintenanceService)
    assert planner._size_memory == build_size_memory(settings.spark)  # noqa: SLF001
    assert planner._claim_lease == compaction_claim_lease(settings)  # noqa: SLF001


def test_the_planner_and_the_candidate_list_use_the_compaction_settings(tmp_path):
    """The planner selects candidates and the list counts partitions per run as the settings say."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    settings.compaction.partitions_per_run = 3
    settings.compaction.quiet_seconds = 45

    async def connect(_temporal: TemporalSettings):
        return MagicMock(name="client")

    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=MagicMock)
    finally:
        bridge.close()

    planner = use_cases.plan_table_maintenance
    candidates = use_cases.list_compaction_candidates
    assert isinstance(planner, PlanTableMaintenanceService)
    assert isinstance(candidates, ListCompactionCandidatesService)
    assert planner._selection == build_candidate_selection(settings.compaction)  # noqa: SLF001
    assert candidates._partitions_per_run == 3  # noqa: SLF001
