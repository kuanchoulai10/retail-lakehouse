"""Test table routes against the real services and in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.service.managed_table.list_managed_tables import (
    ListManagedTablesService,
)
from application.service.managed_table.trigger_maintenance import (
    TriggerMaintenanceService,
)
from application.service.managed_table.update_managed_table_settings import (
    UpdateManagedTableSettingsService,
)
from tests.adapter.inbound.web.web_test_support import build_client
from tests.fakes.in_memory_managed_tables_repo import InMemoryManagedTablesRepo
from tests.fakes.recording_send_table_signal_gateway import (
    RecordingSendTableSignalGateway,
)

NOW = datetime(2026, 10, 24, tzinfo=UTC)


@pytest.fixture
def repo() -> InMemoryManagedTablesRepo:
    repo = InMemoryManagedTablesRepo()
    repo.create(
        ManagedTable.include_manual(
            TableUuid("u-1"),
            TableName("iceberg", "sales", "orders"),
            PolicyTemplateId("t-1"),
            MaintenanceSettings(),
            NOW,
        )
    )
    return repo


@pytest.fixture
def signals() -> RecordingSendTableSignalGateway:
    return RecordingSendTableSignalGateway()


@pytest.fixture
def client(repo, signals):
    return build_client(
        trigger_maintenance=TriggerMaintenanceService(repo, signals),
        update_managed_table_settings=UpdateManagedTableSettingsService(repo, signals),
        list_managed_tables=ListManagedTablesService(repo),
    )


def test_unknown_operation_name_returns_422(client, signals) -> None:
    response = client.post(
        "/v1/tables/u-1/maintenance", json={"operations": ["defragment"]}
    )

    assert response.status_code == 422
    assert signals.calls == []


def test_trigger_unknown_table_returns_404(client) -> None:
    response = client.post(
        "/v1/tables/nope/maintenance", json={"operations": ["rewrite_data_files"]}
    )

    assert response.status_code == 404


def test_trigger_dropped_table_returns_409(client, repo) -> None:
    repo.items["u-1"].mark_dropped(NOW)

    response = client.post(
        "/v1/tables/u-1/maintenance", json={"operations": ["rewrite_data_files"]}
    )

    assert response.status_code == 409


def test_trigger_signals_the_workflow(client, signals) -> None:
    response = client.post(
        "/v1/tables/u-1/maintenance", json={"operations": ["expire_snapshots"]}
    )

    assert response.status_code == 202
    assert [c.signal for c in signals.calls] == ["trigger_now"]


def test_orphan_older_than_below_one_day_returns_422(client) -> None:
    response = client.put(
        "/v1/tables/u-1/settings",
        json={"remove_orphan_files": {"older_than_seconds": 60}},
    )

    assert response.status_code == 422


def test_unknown_nested_settings_key_returns_422(client) -> None:
    response = client.put(
        "/v1/tables/u-1/settings", json={"expire_snapshots": {"keep": 1}}
    )

    assert response.status_code == 422


def test_invalid_status_filter_returns_422(client) -> None:
    response = client.get("/v1/tables", params={"status": "sleepy"})

    assert response.status_code == 422
