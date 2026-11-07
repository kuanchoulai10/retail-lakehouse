"""Test the maintenance run routes."""

from __future__ import annotations

from typing import Any

import pytest

from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetTableMaintenanceRunUseCaseInput,
    GetTableMaintenanceRunUseCaseOutput,
    ListTableMaintenanceRunsUseCaseInput,
    ListTableMaintenanceRunsUseCaseOutput,
    ListTableMaintenanceRunsUseCaseOutputItem,
    ProcessTableMaintenanceCallbackUseCaseInput,
    ProcessTableMaintenanceCallbackUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    ProcessTableMaintenanceCallbackService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_runs_repo import (
    InMemoryTableMaintenanceRunsRepo,
)
from tests.context.table_maintenance.fakes.recording_send_maintenance_result_gateway import (
    RecordingSendMaintenanceResultGateway,
)

FIELDS: dict[str, Any] = {
    "run_id": "run-1",
    "table_uuid": "u-1",
    "execution_ref": "wf-run-1",
    "trigger": "scheduled",
    "status": "running",
    "operations": [{"operation": "rewrite_data_files", "status": "running"}],
    "created_at": NOW,
    "finished_at": None,
}
CALLBACK = {"attempt": 1, "succeeded": True, "metrics": {"rewritten_files": 4}}
URL = "/v1/table-maintenance-runs/run-1/operations/rewrite_data_files/result"


def test_list_runs_of_a_table() -> None:
    item = ListTableMaintenanceRunsUseCaseOutputItem(**FIELDS)
    stub = StubUseCase(ListTableMaintenanceRunsUseCaseOutput(items=[item]))
    client = build_client(list_table_maintenance_runs=stub)

    response = client.get("/v1/tables/u-1/table-maintenance-runs", params={"limit": 5})

    assert response.status_code == 200
    assert response.json()[0]["run_id"] == "run-1"
    assert stub.requests == [ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1", limit=5)]


def test_list_runs_default_limit() -> None:
    stub = StubUseCase(ListTableMaintenanceRunsUseCaseOutput(items=[]))
    client = build_client(list_table_maintenance_runs=stub)

    client.get("/v1/tables/u-1/table-maintenance-runs")

    assert stub.requests == [ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1")]


def test_get_run() -> None:
    stub = StubUseCase(GetTableMaintenanceRunUseCaseOutput(**FIELDS))
    client = build_client(get_table_maintenance_run=stub)

    response = client.get("/v1/table-maintenance-runs/run-1")

    assert response.status_code == 200
    assert response.json()["operations"][0]["operation"] == "rewrite_data_files"
    assert response.json()["execution_ref"] == "wf-run-1"
    assert stub.requests == [GetTableMaintenanceRunUseCaseInput(run_id="run-1")]


def test_callback_returns_202_and_maps_the_body() -> None:
    stub = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=stub)

    response = client.post(URL, json=CALLBACK)

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert stub.requests == [
        ProcessTableMaintenanceCallbackUseCaseInput(
            run_id="run-1",
            operation="rewrite_data_files",
            attempt=1,
            succeeded=True,
            metrics={"rewritten_files": 4},
            error=None,
        )
    ]


def test_callback_accepts_the_runtime_body_with_matching_ids() -> None:
    stub = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=stub)
    body = {
        **CALLBACK,
        "run_id": "run-1",
        "operation": "rewrite_data_files",
        "error": None,
        "extra_runtime_field": "ignored",
    }

    assert client.post(URL, json=body).status_code == 202


@pytest.mark.parametrize("mismatch", [{"run_id": "other"}, {"operation": "expire_snapshots"}])
def test_callback_body_mismatching_the_path_returns_422(mismatch) -> None:
    stub = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=stub)

    response = client.post(URL, json={**CALLBACK, **mismatch})

    assert response.status_code == 422
    assert stub.requests == []


def test_callback_for_unknown_run_returns_404() -> None:
    service = ProcessTableMaintenanceCallbackService(
        InMemoryTableMaintenanceRunsRepo(), RecordingSendMaintenanceResultGateway()
    )
    client = build_client(process_table_maintenance_callback=service)

    response = client.post(URL, json=CALLBACK)

    assert response.status_code == 404


def test_callback_with_unknown_operation_returns_422() -> None:
    service = ProcessTableMaintenanceCallbackService(
        InMemoryTableMaintenanceRunsRepo(), RecordingSendMaintenanceResultGateway()
    )
    client = build_client(process_table_maintenance_callback=service)

    response = client.post("/v1/table-maintenance-runs/run-1/operations/defragment/result", json=CALLBACK)

    assert response.status_code == 422


def test_old_run_routes_are_gone() -> None:
    client = build_client()

    assert client.get("/v1/runs/run-1").status_code == 404
    assert client.get("/v1/tables/u-1/runs").status_code == 404
    old = "/v1/runs/run-1/operations/rewrite_data_files/result"
    assert client.post(old, json=CALLBACK).status_code == 404
