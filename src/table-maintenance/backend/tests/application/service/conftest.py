"""Shared fixtures for application service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from tests.fakes.fake_read_catalog_gateway import FakeReadCatalogGateway
from tests.fakes.in_memory_discovery_rules_repo import InMemoryDiscoveryRulesRepo
from tests.fakes.in_memory_discovery_settings_repo import (
    InMemoryDiscoverySettingsRepo,
)
from tests.fakes.in_memory_managed_tables_repo import InMemoryManagedTablesRepo
from tests.fakes.in_memory_policy_templates_repo import InMemoryPolicyTemplatesRepo
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
def templates_repo() -> InMemoryPolicyTemplatesRepo:
    return InMemoryPolicyTemplatesRepo()


@pytest.fixture
def rules_repo() -> InMemoryDiscoveryRulesRepo:
    return InMemoryDiscoveryRulesRepo()


@pytest.fixture
def discovery_settings_repo() -> InMemoryDiscoverySettingsRepo:
    return InMemoryDiscoverySettingsRepo(NOW)


@pytest.fixture
def tables_repo() -> InMemoryManagedTablesRepo:
    return InMemoryManagedTablesRepo()


@pytest.fixture
def signals() -> RecordingSendTableSignalGateway:
    return RecordingSendTableSignalGateway()


@pytest.fixture
def schedule() -> RecordingUpdateDiscoveryScheduleGateway:
    return RecordingUpdateDiscoveryScheduleGateway()


@pytest.fixture
def catalog() -> FakeReadCatalogGateway:
    return FakeReadCatalogGateway()
