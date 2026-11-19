"""Test the table routes with stub use cases."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

from context.table_maintenance.application.exceptions import ConflictError, NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableUseCaseInput,
    GetTableUseCaseOutput,
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
    SetTablePriorityUseCaseOutput,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableMaintenanceUseCaseOutput,
    TriggerTableReconciliationUseCaseInput,
    TriggerTableReconciliationUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)

FIELDS: dict[str, Any] = {
    "uuid": "u-1",
    "catalog": "iceberg",
    "namespace": "sales",
    "table": "orders",
    "status": "managed",
    "priority": "P3",
    "matched_rule_id": "dr-01h455vb4pex5vsknk084sn02q",
    "operation_states": {"rewrite_data_files": {"last_attempt_at": NOW, "consecutive_failures": 0}},
    "registered_at": NOW,
    "updated_at": NOW,
    "last_committed_at": NOW - timedelta(minutes=5),
    "last_discovered_at": NOW - timedelta(minutes=10),
}


def test_list_tables_passes_the_status_filter() -> None:
    """Listing tables passes the status filter to the use case."""
    item = ListTablesUseCaseOutput.Table(**FIELDS)
    stub = StubUseCase(ListTablesUseCaseOutput(items=(item,)))
    client = build_client(list_tables=stub)

    response = client.get("/v1/tables", params={"status": "managed"})

    assert response.status_code == 200
    assert response.json()[0]["uuid"] == "u-1"
    assert stub.requests == [ListTablesUseCaseInput(status="managed")]


def test_list_tables_answers_the_last_commit_and_the_last_discovery() -> None:
    """Each listed table carries when it was last committed to and last discovered, null when unknown."""
    known = ListTablesUseCaseOutput.Table(**FIELDS)
    unknown = ListTablesUseCaseOutput.Table(
        **(known.model_dump() | {"uuid": "u-2", "last_committed_at": None, "last_discovered_at": None})
    )
    client = build_client(list_tables=StubUseCase(ListTablesUseCaseOutput(items=(known, unknown))))

    body = client.get("/v1/tables").json()

    assert [(_at(t["last_committed_at"]), _at(t["last_discovered_at"])) for t in body] == [
        (NOW - timedelta(minutes=5), NOW - timedelta(minutes=10)),
        (None, None),
    ]


def _at(text: str | None) -> datetime | None:
    return None if text is None else datetime.fromisoformat(text)


def test_list_tables_without_filter() -> None:
    """Listing tables without a filter passes no status."""
    stub = StubUseCase(ListTablesUseCaseOutput(items=()))
    client = build_client(list_tables=stub)

    response = client.get("/v1/tables")

    assert response.json() == []
    assert stub.requests == [ListTablesUseCaseInput(status=None)]


def test_get_table() -> None:
    """Getting a table returns its name and per-operation states."""
    stub = StubUseCase(GetTableUseCaseOutput(**FIELDS))
    client = build_client(get_table=stub)

    response = client.get("/v1/tables/u-1")

    body = response.json()
    assert response.status_code == 200
    assert body["table"] == "orders"
    assert body["operation_states"]["rewrite_data_files"]["consecutive_failures"] == 0
    assert stub.requests == [GetTableUseCaseInput(uuid="u-1")]


def test_get_table_has_no_selection_settings_or_preset() -> None:
    """A table answers its status and deciding rule, nothing about manual selection, settings or presets."""
    client = build_client(get_table=StubUseCase(GetTableUseCaseOutput(**FIELDS)))

    body = client.get("/v1/tables/u-1").json()

    assert body["status"] == "managed"
    assert not {"selection", "settings", "source_preset_id"} & body.keys()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/v1/tables/u-1/pause"),
        ("post", "/v1/tables/u-1/resume"),
        ("post", "/v1/tables/u-1/reset-selection"),
        ("put", "/v1/tables/u-1/settings"),
        ("post", "/v1/tables/include"),
        ("post", "/v1/tables/exclude"),
    ],
)
def test_manual_selection_and_settings_routes_are_gone(method: str, path: str) -> None:
    """Pausing, resuming, including, excluding, resetting the selection and table settings are no longer served."""
    client = build_client()

    response = client.request(method, path, json={})

    assert response.status_code in (404, 405)


def test_trigger_table_maintenance_returns_202() -> None:
    """Triggering maintenance returns 202 and passes the table and operations to the use case."""
    stub = StubUseCase(TriggerTableMaintenanceUseCaseOutput(accepted=True))
    client = build_client(trigger_table_maintenance=stub)

    response = client.post("/v1/tables/u-1/maintenance", json={"operations": ["rewrite_data_files"]})

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert stub.requests == [TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=("rewrite_data_files",))]


def test_put_priority_sets_it_then_answers_the_table() -> None:
    """Setting the priority passes the table and priority to the use case and answers the table read back."""
    set_stub = StubUseCase(SetTablePriorityUseCaseOutput(uuid="u-1", priority="P1"))
    get_stub = StubUseCase(GetTableUseCaseOutput(**(GetTableUseCaseOutput(**FIELDS).model_dump() | {"priority": "P1"})))
    client = build_client(set_table_priority=set_stub, get_table=get_stub)

    response = client.put("/v1/tables/u-1/priority", json={"priority": "P1"})

    assert response.status_code == 200
    assert response.json()["priority"] == "P1"
    assert [(r.uuid, r.priority) for r in set_stub.requests] == [("u-1", "P1")]
    assert get_stub.requests == [GetTableUseCaseInput(uuid="u-1")]


def test_reconcile_table_returns_202() -> None:
    """Reconciling a table now returns 202 and passes the table to the use case."""
    stub = StubUseCase(TriggerTableReconciliationUseCaseOutput(accepted=True))
    client = build_client(trigger_table_reconciliation=stub)

    response = client.post("/v1/tables/u-1/reconcile")

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert stub.requests == [TriggerTableReconciliationUseCaseInput(uuid="u-1")]


@pytest.mark.parametrize(
    ("error", "code"),
    [(NotFoundError("table nope not found"), 404), (ConflictError("table u-1 is unmanaged"), 409)],
    ids=["unknown", "unmanaged"],
)
def test_reconcile_table_maps_errors(error: Exception, code: int) -> None:
    """An unknown table is 404 and a table out of maintenance is 409."""
    client = build_client(trigger_table_reconciliation=StubUseCase(error=error))

    response = client.post("/v1/tables/u-1/reconcile")

    assert response.status_code == code
