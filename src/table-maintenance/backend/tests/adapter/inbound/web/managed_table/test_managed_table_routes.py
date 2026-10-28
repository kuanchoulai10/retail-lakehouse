"""Test the managed table routes with stub use cases."""

from __future__ import annotations

from typing import Any

import pytest
from application.port.inbound.managed_table.exclude_managed_table import (
    ExcludeManagedTableUseCaseInput,
    ExcludeManagedTableUseCaseOutput,
)
from application.port.inbound.managed_table.get_managed_table import (
    GetManagedTableUseCaseInput,
    GetManagedTableUseCaseOutput,
)
from application.port.inbound.managed_table.include_managed_table import (
    IncludeManagedTableUseCaseInput,
    IncludeManagedTableUseCaseOutput,
)
from application.port.inbound.managed_table.list_managed_tables import (
    ListManagedTablesUseCaseInput,
    ListManagedTablesUseCaseOutput,
    ListManagedTablesUseCaseOutputItem,
)
from application.port.inbound.managed_table.pause_managed_table import (
    PauseManagedTableUseCaseInput,
    PauseManagedTableUseCaseOutput,
)
from application.port.inbound.managed_table.reset_managed_table_selection import (
    ResetManagedTableSelectionUseCaseInput,
    ResetManagedTableSelectionUseCaseOutput,
)
from application.port.inbound.managed_table.resume_managed_table import (
    ResumeManagedTableUseCaseInput,
    ResumeManagedTableUseCaseOutput,
)
from application.port.inbound.managed_table.trigger_maintenance import (
    TriggerMaintenanceUseCaseInput,
    TriggerMaintenanceUseCaseOutput,
)
from application.port.inbound.managed_table.update_managed_table_settings import (
    UpdateManagedTableSettingsUseCaseInput,
    UpdateManagedTableSettingsUseCaseOutput,
)
from tests.adapter.inbound.web.web_test_support import NOW, StubUseCase, build_client

FIELDS: dict[str, Any] = {
    "uuid": "u-1",
    "catalog": "iceberg",
    "namespace": "sales",
    "table": "orders",
    "status": "active",
    "selection": "auto",
    "settings": {"reconcile_interval_seconds": 3600},
    "matched_rule_id": "r-1",
    "source_preset_id": "t-1",
    "operation_states": {
        "rewrite_data_files": {"last_attempt_at": NOW, "consecutive_failures": 0}
    },
    "registered_at": NOW,
    "updated_at": NOW,
}


def test_list_tables_passes_the_status_filter() -> None:
    item = ListManagedTablesUseCaseOutputItem(**FIELDS)
    stub = StubUseCase(ListManagedTablesUseCaseOutput(items=[item]))
    client = build_client(list_managed_tables=stub)

    response = client.get("/v1/tables", params={"status": "active"})

    assert response.status_code == 200
    assert response.json()[0]["uuid"] == "u-1"
    assert stub.requests == [ListManagedTablesUseCaseInput(status="active")]


def test_list_tables_without_filter() -> None:
    stub = StubUseCase(ListManagedTablesUseCaseOutput(items=[]))
    client = build_client(list_managed_tables=stub)

    response = client.get("/v1/tables")

    assert response.json() == []
    assert stub.requests == [ListManagedTablesUseCaseInput(status=None)]


def test_get_table() -> None:
    stub = StubUseCase(GetManagedTableUseCaseOutput(**FIELDS))
    client = build_client(get_managed_table=stub)

    response = client.get("/v1/tables/u-1")

    body = response.json()
    assert response.status_code == 200
    assert body["table"] == "orders"
    assert body["operation_states"]["rewrite_data_files"]["consecutive_failures"] == 0
    assert stub.requests == [GetManagedTableUseCaseInput(uuid="u-1")]


def test_put_settings_sends_the_body_as_settings() -> None:
    stub = StubUseCase(UpdateManagedTableSettingsUseCaseOutput(**FIELDS))
    client = build_client(update_managed_table_settings=stub)
    settings = {"expire_snapshots": {"retain_last": 5}}

    response = client.put("/v1/tables/u-1/settings", json=settings)

    assert response.status_code == 200
    assert stub.requests == [
        UpdateManagedTableSettingsUseCaseInput(uuid="u-1", settings=settings)
    ]


@pytest.mark.parametrize(
    ("action", "field", "port_input", "port_output"),
    [
        (
            "pause",
            "pause_managed_table",
            PauseManagedTableUseCaseInput,
            PauseManagedTableUseCaseOutput,
        ),
        (
            "resume",
            "resume_managed_table",
            ResumeManagedTableUseCaseInput,
            ResumeManagedTableUseCaseOutput,
        ),
        (
            "reset-selection",
            "reset_managed_table_selection",
            ResetManagedTableSelectionUseCaseInput,
            ResetManagedTableSelectionUseCaseOutput,
        ),
    ],
)
def test_lifecycle_actions(action, field, port_input, port_output) -> None:
    stub = StubUseCase(port_output(**FIELDS))
    client = build_client(**{field: stub})

    response = client.post(f"/v1/tables/u-1/{action}")

    assert response.status_code == 200
    assert response.json()["uuid"] == "u-1"
    assert stub.requests == [port_input(uuid="u-1")]


def test_include_table() -> None:
    stub = StubUseCase(IncludeManagedTableUseCaseOutput(**FIELDS))
    client = build_client(include_managed_table=stub)
    body = {
        "catalog": "iceberg",
        "namespace": "sales",
        "table": "orders",
        "preset_id": "t-1",
    }

    response = client.post("/v1/tables/include", json=body)

    assert response.status_code == 200
    assert stub.requests == [IncludeManagedTableUseCaseInput(**body)]


def test_exclude_table() -> None:
    stub = StubUseCase(ExcludeManagedTableUseCaseOutput(**FIELDS))
    client = build_client(exclude_managed_table=stub)
    body = {"catalog": "iceberg", "namespace": "sales", "table": "orders"}

    response = client.post("/v1/tables/exclude", json=body)

    assert response.status_code == 200
    assert stub.requests == [ExcludeManagedTableUseCaseInput(**body)]


def test_trigger_maintenance_returns_202() -> None:
    stub = StubUseCase(TriggerMaintenanceUseCaseOutput(accepted=True))
    client = build_client(trigger_maintenance=stub)

    response = client.post(
        "/v1/tables/u-1/maintenance", json={"operations": ["rewrite_data_files"]}
    )

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert stub.requests == [
        TriggerMaintenanceUseCaseInput(uuid="u-1", operations=["rewrite_data_files"])
    ]
