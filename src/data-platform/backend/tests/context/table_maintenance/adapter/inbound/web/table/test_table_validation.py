"""Test table routes against the real services and in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.service.table import (
    GetTableService,
    ListTablesService,
    SetTablePriorityService,
    TriggerTableMaintenanceService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    build_client,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, UNMANAGED
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import (
    InMemoryCatalogDiscoveriesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
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
        Table.register(
            TableId("u-1"),
            TableName(catalog="iceberg", namespace="sales", table="orders"),
            MANAGED,
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
        set_table_priority=SetTablePriorityService(repo, clock=lambda: NOW),
        get_table=GetTableService(repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo()),
        list_tables=ListTablesService(repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo()),
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


def test_trigger_unmanaged_table_returns_409(client, repo, signals) -> None:
    """Triggering maintenance on an unmanaged table returns 409 and sends nothing."""
    repo.items["u-1"].unmanage(UNMANAGED.decided_by, NOW)

    response = client.post("/v1/tables/u-1/maintenance", json={"operations": ["rewrite_data_files"]})

    assert response.status_code == 409
    assert signals.calls == []


def test_status_filter_lists_unmanaged_tables(client, repo) -> None:
    """The status filter takes the managed, unmanaged and dropped statuses."""
    repo.items["u-1"].unmanage(UNMANAGED.decided_by, NOW)

    assert [t["uuid"] for t in client.get("/v1/tables", params={"status": "unmanaged"}).json()] == ["u-1"]
    assert client.get("/v1/tables", params={"status": "managed"}).json() == []


def test_invalid_status_filter_returns_422(client) -> None:
    """An invalid table status filter is rejected with 422."""
    response = client.get("/v1/tables", params={"status": "sleepy"})

    assert response.status_code == 422


def test_put_priority_returns_the_table(client, repo) -> None:
    """Setting the priority answers the updated table and saves it."""
    response = client.put("/v1/tables/u-1/priority", json={"priority": "P1"})

    assert response.status_code == 200
    assert response.json()["uuid"] == "u-1"
    assert response.json()["priority"] == "P1"
    assert repo.items["u-1"].priority.value == "P1"


def test_put_priority_rejects_p4(client, repo) -> None:
    """An unknown priority is rejected with 422 and changes nothing."""
    response = client.put("/v1/tables/u-1/priority", json={"priority": "P4"})

    assert response.status_code == 422
    assert repo.items["u-1"].priority.value == "P3"


def test_put_priority_rejects_extra_fields(client) -> None:
    """The body takes only the priority."""
    response = client.put("/v1/tables/u-1/priority", json={"priority": "P1", "note": "x"})

    assert response.status_code == 422


def test_put_priority_unknown_table_returns_404(client) -> None:
    """Setting the priority of an unknown table returns 404."""
    response = client.put("/v1/tables/nope/priority", json={"priority": "P1"})

    assert response.status_code == 404


def test_put_priority_dropped_table_returns_409(client, repo) -> None:
    """Setting the priority of a dropped table returns 409."""
    repo.items["u-1"].mark_dropped(NOW)

    response = client.put("/v1/tables/u-1/priority", json={"priority": "P1"})

    assert response.status_code == 409


def test_get_table_shows_priority(client) -> None:
    """A new table shows P3 in the detail and in the list."""
    assert client.get("/v1/tables/u-1").json()["priority"] == "P3"
    assert [t["priority"] for t in client.get("/v1/tables").json()] == ["P3"]
