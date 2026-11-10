"""Test table routes against the real services and in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
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
    """Provide an in-memory table repository."""
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
    """Provide a table change gateway that records its calls."""
    return RecordingSendTableChangeGateway()


@pytest.fixture
def client(repo, signals):
    """Provide a test client wired to the repository and the signal gateway."""
    return build_client(
        trigger_table_maintenance=TriggerTableMaintenanceService(repo, signals),
        update_table_settings=UpdateTableSettingsService(repo, signals),
        list_tables=ListTablesService(repo),
    )


def test_unknown_operation_name_returns_422(client, signals) -> None:
    """An unknown operation name is rejected with 422 and sends no signal."""
    response = client.post("/v1/tables/u-1/maintenance", json={"operations": ["defragment"]})

    assert response.status_code == 422
    assert signals.calls == []


def test_trigger_unknown_table_returns_404(client) -> None:
    """Triggering maintenance on an unknown table returns 404."""
    response = client.post("/v1/tables/nope/maintenance", json={"operations": ["rewrite_data_files"]})

    assert response.status_code == 404


def test_trigger_dropped_table_returns_409(client, repo) -> None:
    """Triggering maintenance on a dropped table returns 409."""
    repo.items["u-1"].mark_dropped(NOW)

    response = client.post("/v1/tables/u-1/maintenance", json={"operations": ["rewrite_data_files"]})

    assert response.status_code == 409


def test_trigger_signals_the_workflow(client, signals) -> None:
    """Triggering maintenance returns 202 and sends a maintenance requested change."""
    response = client.post("/v1/tables/u-1/maintenance", json={"operations": ["expire_snapshots"]})

    assert response.status_code == 202
    assert [c.change for c in signals.calls] == ["maintenance_requested"]


def test_orphan_older_than_below_one_day_returns_422(client) -> None:
    """An orphan retention below one day is rejected with 422."""
    response = client.put(
        "/v1/tables/u-1/settings",
        json={"remove_orphan_files": {"older_than_seconds": 60}},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "remove_orphan_files.older_than_seconds: must be at least 1 day"}


def test_unknown_nested_settings_key_returns_422(client) -> None:
    """An unknown key in nested settings is rejected with 422."""
    response = client.put("/v1/tables/u-1/settings", json={"expire_snapshots": {"keep": 1}})

    assert response.status_code == 422
    assert response.json() == {"detail": "expire_snapshots.keep: Extra inputs are not permitted"}


@pytest.mark.parametrize(
    ("settings", "detail"),
    [
        ({"dry_run": 1}, "dry_run: Input should be a valid boolean"),
        (
            {"rewrite_data_files": {"min_reducible_files": True}},
            "rewrite_data_files.min_reducible_files: Input should be a valid integer",
        ),
        (
            {"reconcile_interval_seconds": 1.5},
            "reconcile_interval_seconds: must be a whole number of seconds",
        ),
        ({"reconcile_interval": 3600}, "reconcile_interval: Extra inputs are not permitted"),
        ({"reconcile_interval_seconds": 10**15}, "reconcile_interval_seconds: too large for a duration"),
    ],
)
def test_mistyped_settings_return_422_with_one_line(client, settings, detail) -> None:
    """A mistyped value, a field name instead of its wire name, or out-of-range seconds answer 422 in one line."""
    response = client.put("/v1/tables/u-1/settings", json=settings)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_invalid_status_filter_returns_422(client) -> None:
    """An invalid table status filter is rejected with 422."""
    response = client.get("/v1/tables", params={"status": "sleepy"})

    assert response.status_code == 422
