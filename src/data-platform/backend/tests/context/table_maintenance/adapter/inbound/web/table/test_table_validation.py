"""Test table routes against the real services and in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableName,
    TableId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.service.table import (
    ListTablesService,
    TriggerTableMaintenanceService,
    UpdateTableSettingsService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    build_client,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import (
    InMemoryTablesRepo,
)
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

NOW = datetime(2026, 10, 24, tzinfo=UTC)


@pytest.fixture
def repo() -> InMemoryTablesRepo:
    repo = InMemoryTablesRepo()
    repo.create(
        Table.include_manual(
            TableId("u-1"),
            TableName("iceberg", "sales", "orders"),
            TableMaintenancePresetId("t-1"),
            MaintenanceSettings(),
            NOW,
        )
    )
    return repo


@pytest.fixture
def signals() -> RecordingSendTableChangeGateway:
    return RecordingSendTableChangeGateway()


@pytest.fixture
def client(repo, signals):
    return build_client(
        trigger_table_maintenance=TriggerTableMaintenanceService(repo, signals),
        update_table_settings=UpdateTableSettingsService(repo, signals),
        list_tables=ListTablesService(repo),
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
    assert [c.change for c in signals.calls] == ["maintenance_requested"]


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
