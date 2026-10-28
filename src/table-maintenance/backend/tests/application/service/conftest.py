"""Shared fixtures for application service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from tests.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.fakes.fake_read_maintenance_job_gateway import (
    FakeReadMaintenanceJobGateway,
)
from tests.fakes.in_memory_maintenance_runs_repo import InMemoryMaintenanceRunsRepo
from tests.fakes.recording_delete_maintenance_job_gateway import (
    RecordingDeleteMaintenanceJobGateway,
)
from tests.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.fakes.recording_send_maintenance_result_gateway import (
    RecordingSendMaintenanceResultGateway,
)
from tests.fakes.recording_submit_maintenance_job_gateway import (
    RecordingSubmitMaintenanceJobGateway,
)
from tests.fakes.in_memory_discovery_rules_repo import InMemoryDiscoveryRulesRepo
from tests.fakes.in_memory_discovery_settings_repo import (
    InMemoryDiscoverySettingsRepo,
)
from tests.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.fakes.in_memory_table_maintenance_presets_repo import (
    InMemoryTableMaintenancePresetsRepo,
)
from tests.fakes.recording_send_table_signal_gateway import (
    RecordingSendTableSignalGateway,
)
from tests.fakes.recording_update_discovery_schedule_gateway import (
    RecordingUpdateDiscoveryScheduleGateway,
)

if TYPE_CHECKING:
    from collections.abc import Callable

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def clock() -> Callable[[], datetime]:
    return lambda: NOW


@pytest.fixture
def new_id() -> Callable[[], str]:
    counter = iter(range(1, 1000))
    return lambda: f"id-{next(counter)}"


@pytest.fixture
def presets_repo() -> InMemoryTableMaintenancePresetsRepo:
    return InMemoryTableMaintenancePresetsRepo()


@pytest.fixture
def rules_repo() -> InMemoryDiscoveryRulesRepo:
    return InMemoryDiscoveryRulesRepo()


@pytest.fixture
def discovery_settings_repo() -> InMemoryDiscoverySettingsRepo:
    return InMemoryDiscoverySettingsRepo(NOW)


@pytest.fixture
def tables_repo() -> InMemoryTablesRepo:
    return InMemoryTablesRepo()


@pytest.fixture
def signals() -> RecordingSendTableSignalGateway:
    return RecordingSendTableSignalGateway()


@pytest.fixture
def schedule() -> RecordingUpdateDiscoveryScheduleGateway:
    return RecordingUpdateDiscoveryScheduleGateway()


@pytest.fixture
def catalog() -> FakeReadTableMetadataGateway:
    return FakeReadTableMetadataGateway()


@pytest.fixture
def runs_repo() -> InMemoryMaintenanceRunsRepo:
    return InMemoryMaintenanceRunsRepo()


@pytest.fixture
def submit_job() -> RecordingSubmitMaintenanceJobGateway:
    return RecordingSubmitMaintenanceJobGateway()


@pytest.fixture
def read_job() -> FakeReadMaintenanceJobGateway:
    return FakeReadMaintenanceJobGateway()


@pytest.fixture
def delete_job() -> RecordingDeleteMaintenanceJobGateway:
    return RecordingDeleteMaintenanceJobGateway()


@pytest.fixture
def results() -> RecordingSendMaintenanceResultGateway:
    return RecordingSendMaintenanceResultGateway()


@pytest.fixture
def discovery_requests() -> RecordingSendDiscoveryRequestGateway:
    return RecordingSendDiscoveryRequestGateway()


@pytest.fixture
def log() -> list[tuple[str, str]]:
    return []
