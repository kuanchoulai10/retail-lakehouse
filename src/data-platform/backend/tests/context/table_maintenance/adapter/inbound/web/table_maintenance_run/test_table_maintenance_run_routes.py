"""Test the maintenance run routes."""

from __future__ import annotations

from typing import Any

import pytest

from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetTableMaintenanceRunUseCaseInput,
    GetTableMaintenanceRunUseCaseOutput,
    ListTableMaintenanceRunsUseCaseInput,
    ListTableMaintenanceRunsUseCaseOutput,
    ProcessTableMaintenanceCallbackUseCaseInput,
    ProcessTableMaintenanceCallbackUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetTableMaintenanceRunService,
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

RUN_ID = "mr-01kaa4zc9qf3v8d2m6xk0w7b1n"
FIELDS: dict[str, Any] = {
    "run_id": RUN_ID,
    "table_uuid": "u-1",
    "execution_ref": "wf-run-1",
    "trigger": "scheduled",
    "priority": "P1",
    "status": "running",
    "operations": (
        {
            "operation": "rewrite_data_files",
            "status": "running",
            "attempts": 2,
            "started_at": NOW,
            "finished_at": None,
            "job_name": f"{RUN_ID}-rewrite_data_files-2",
            "metrics": {},
            "error": None,
            "expected_files": None,
            "attempt_history": [
                {
                    "attempt": 1,
                    "size": "S",
                    "status": "failed",
                    "started_at": NOW,
                    "finished_at": NOW,
                    "failure_class": "oom",
                    "error": "java.lang.OutOfMemoryError: Java heap space",
                    "event_log_finished": False,
                    "next_step": "retry_larger",
                    "next_size": "M",
                },
                {
                    "attempt": 2,
                    "size": "M",
                    "status": "running",
                    "started_at": NOW,
                    "finished_at": None,
                    "failure_class": None,
                    "error": None,
                    "event_log_finished": None,
                    "next_step": None,
                    "next_size": None,
                },
            ],
        },
    ),
    "created_at": NOW,
    "finished_at": None,
}
CALLBACK = {"attempt": 1, "succeeded": True, "metrics": {"rewritten_files": 4}}
URL = f"/v1/table-maintenance-runs/{RUN_ID}/operations/rewrite_data_files/result"
OLD_UUID_RUN_ID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
RUN_ID_SHAPE = "TableMaintenanceRunId must look like mr-<26 base32 characters>"


def test_list_runs_of_a_table() -> None:
    """Listing runs of a table passes the table and limit to the use case."""
    item = ListTableMaintenanceRunsUseCaseOutput.TableMaintenanceRun(**FIELDS)
    stub = StubUseCase(ListTableMaintenanceRunsUseCaseOutput(items=(item,)))
    client = build_client(list_table_maintenance_runs=stub)

    response = client.get("/v1/tables/u-1/table-maintenance-runs", params={"limit": 5})

    assert response.status_code == 200
    assert response.json()[0]["run_id"] == RUN_ID
    assert stub.requests == [ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1", limit=5)]


def test_list_runs_default_limit() -> None:
    """Listing runs without a limit leaves the limit to the use case default."""
    stub = StubUseCase(ListTableMaintenanceRunsUseCaseOutput(items=()))
    client = build_client(list_table_maintenance_runs=stub)

    client.get("/v1/tables/u-1/table-maintenance-runs")

    assert stub.requests == [ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1")]


def test_get_run() -> None:
    """Getting a run returns its operations and execution reference."""
    stub = StubUseCase(GetTableMaintenanceRunUseCaseOutput(**FIELDS))
    client = build_client(get_table_maintenance_run=stub)

    response = client.get(f"/v1/table-maintenance-runs/{RUN_ID}")

    assert response.status_code == 200
    assert response.json()["operations"][0]["operation"] == "rewrite_data_files"
    assert response.json()["execution_ref"] == "wf-run-1"
    assert response.json()["priority"] == "P1"
    assert stub.requests == [GetTableMaintenanceRunUseCaseInput(run_id=RUN_ID)]


def test_run_response_lists_each_attempt() -> None:
    """A run's operation lists every attempt with its size, failure class and what followed it."""
    client = build_client(get_table_maintenance_run=StubUseCase(GetTableMaintenanceRunUseCaseOutput(**FIELDS)))

    operation = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()["operations"][0]

    assert operation["attempt_history"][1]["size"] == "M"
    assert operation["attempt_history"][0] == {
        "attempt": 1,
        "size": "S",
        "status": "failed",
        "started_at": NOW.isoformat().replace("+00:00", "Z"),
        "finished_at": NOW.isoformat().replace("+00:00", "Z"),
        "failure_class": "oom",
        "error": "java.lang.OutOfMemoryError: Java heap space",
        "event_log_finished": False,
        "next_step": "retry_larger",
        "next_size": "M",
    }


def test_run_schema_types_its_operations_and_attempts() -> None:
    """The OpenAPI schema names the operation and attempt shapes instead of a free-form object."""
    schemas = build_client().get("/openapi.json").json()["components"]["schemas"]

    operations = schemas["TableMaintenanceRunApiResponse"]["properties"]["operations"]
    assert operations["items"] == {"$ref": "#/components/schemas/TableMaintenanceRunOperationApiResponse"}
    history = schemas["TableMaintenanceRunOperationApiResponse"]["properties"]["attempt_history"]
    assert history["items"] == {"$ref": "#/components/schemas/TableMaintenanceRunAttemptApiResponse"}


def test_callback_returns_202_and_maps_the_body() -> None:
    """The callback returns 202 and maps its body to the record result input."""
    stub = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=stub)

    response = client.post(URL, json=CALLBACK)

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert stub.requests == [
        ProcessTableMaintenanceCallbackUseCaseInput(
            run_id=RUN_ID,
            operation="rewrite_data_files",
            attempt=1,
            succeeded=True,
            metrics={"rewritten_files": 4},
            error=None,
        )
    ]


def test_callback_accepts_the_runtime_body_with_matching_ids() -> None:
    """The callback accepts the body the Spark runtime sends when its ids match the path."""
    stub = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=stub)
    body = {
        **CALLBACK,
        "run_id": RUN_ID,
        "operation": "rewrite_data_files",
        "error": None,
        "extra_runtime_field": "ignored",
    }

    assert client.post(URL, json=body).status_code == 202


@pytest.mark.parametrize("mismatch", [{"run_id": "other"}, {"operation": "expire_snapshots"}])
def test_callback_body_mismatching_the_path_returns_422(mismatch) -> None:
    """A callback body whose ids differ from the path is rejected with 422 and not recorded."""
    stub = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=stub)

    response = client.post(URL, json={**CALLBACK, **mismatch})

    assert response.status_code == 422
    assert stub.requests == []


def test_callback_for_unknown_run_returns_404() -> None:
    """A callback for an unknown run returns 404."""
    service = ProcessTableMaintenanceCallbackService(
        InMemoryTableMaintenanceRunsRepo(), RecordingSendMaintenanceResultGateway()
    )
    client = build_client(process_table_maintenance_callback=service)

    response = client.post(URL, json=CALLBACK)

    assert response.status_code == 404


def test_callback_with_unknown_operation_returns_422() -> None:
    """A callback with an unknown operation is rejected with 422."""
    service = ProcessTableMaintenanceCallbackService(
        InMemoryTableMaintenanceRunsRepo(), RecordingSendMaintenanceResultGateway()
    )
    client = build_client(process_table_maintenance_callback=service)

    response = client.post(f"/v1/table-maintenance-runs/{RUN_ID}/operations/defragment/result", json=CALLBACK)

    assert response.status_code == 422


def test_old_run_routes_are_gone() -> None:
    """The old run routes return 404."""
    client = build_client()

    assert client.get("/v1/runs/run-1").status_code == 404
    assert client.get("/v1/tables/u-1/runs").status_code == 404
    old = "/v1/runs/run-1/operations/rewrite_data_files/result"
    assert client.post(old, json=CALLBACK).status_code == 404


def test_get_run_with_an_old_uuid_is_422() -> None:
    """A run id of the old UUID shape answers 422 naming the mr- shape, not 404."""
    client = build_client(get_table_maintenance_run=GetTableMaintenanceRunService(InMemoryTableMaintenanceRunsRepo()))

    response = client.get(f"/v1/table-maintenance-runs/{OLD_UUID_RUN_ID}")

    assert response.status_code == 422
    assert RUN_ID_SHAPE in response.json()["detail"]


def test_callback_with_an_old_uuid_is_422() -> None:
    """A callback naming a run id of the old UUID shape answers 422 naming the mr- shape and sends nothing."""
    results = RecordingSendMaintenanceResultGateway()
    service = ProcessTableMaintenanceCallbackService(InMemoryTableMaintenanceRunsRepo(), results)
    client = build_client(process_table_maintenance_callback=service)

    response = client.post(
        f"/v1/table-maintenance-runs/{OLD_UUID_RUN_ID}/operations/rewrite_data_files/result", json=CALLBACK
    )

    assert response.status_code == 422
    assert RUN_ID_SHAPE in response.json()["detail"]
    assert results.calls == []


def _path_parameter(path: str, method: str, name: str) -> dict:
    operation = build_client().get("/openapi.json").json()["paths"][path][method]
    return next(p for p in operation["parameters"] if p["name"] == name)


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/v1/table-maintenance-runs/{run_id}", "get"),
        ("/v1/table-maintenance-runs/{run_id}/operations/{operation}/result", "post"),
    ],
)
def test_run_id_path_parameter_describes_its_shape(path: str, method: str) -> None:
    """The ``run_id`` parameter tells an API user the ``mr-`` shape, with no pattern of its own."""
    parameter = _path_parameter(path, method, "run_id")
    assert "`mr-`" in parameter["description"]
    assert "ADR 0011" in parameter["description"]
    assert "pattern" not in parameter["schema"]
