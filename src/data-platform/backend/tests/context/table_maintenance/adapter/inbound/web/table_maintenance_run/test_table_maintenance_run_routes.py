"""Test the maintenance run routes."""

from __future__ import annotations

from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    PartitionFieldInfo,
    PartitionSpecInfo,
    SpecPartitions,
    TableId,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    ExpireSnapshotsJobContent,
    RewriteDataFilesJobContent,
    TableMaintenanceRun,
    TriggerType,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    ForwardTableMaintenanceResultUseCaseInput,
    ForwardTableMaintenanceResultUseCaseOutput,
    GetTableMaintenanceRunUseCaseInput,
    GetTableMaintenanceRunUseCaseOutput,
    ListTableMaintenanceRunsUseCaseInput,
    ListTableMaintenanceRunsUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    ForwardTableMaintenanceResultService,
    GetTableMaintenanceRunService,
    ListTableMaintenanceRunsService,
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
ATTEMPT_1: dict[str, Any] = {
    "attempt": 1,
    "size": "S",
    "status": "failed",
    "job_name": f"{RUN_ID}-rewrite_data_files-1",
    "started_at": NOW,
    "started_running_at": NOW,
    "finished_at": NOW,
    "failure_class": "oom",
    "error": "java.lang.OutOfMemoryError: Java heap space",
    "event_log_finished": False,
    "next_step": "retry_larger",
    "next_size": "M",
}
ATTEMPT_2: dict[str, Any] = {
    "attempt": 2,
    "size": "M",
    "status": "queued",
    "job_name": f"{RUN_ID}-rewrite_data_files-2",
    "started_at": NOW,
    "started_running_at": None,
    "finished_at": None,
    "failure_class": None,
    "error": None,
    "event_log_finished": None,
    "next_step": None,
    "next_size": None,
}
FIELDS: dict[str, Any] = {
    "run_id": RUN_ID,
    "table_uuid": "u-1",
    "execution_ref": "wf-run-1",
    "trigger": "scheduled",
    "priority": "P1",
    "operation": "rewrite_data_files",
    "status": "queued",
    "content": {
        "operation": "rewrite_data_files",
        "target_file_size_bytes": 536870912,
        "options": {},
        "partitions": [],
    },
    "metrics": {},
    "error": None,
    "skip_reason": None,
    "created_at": NOW,
    "started_at": NOW,
    "finished_at": None,
    "attempts": (ATTEMPT_1, ATTEMPT_2),
}
CALLBACK = {"attempt": 1, "succeeded": True, "metrics": {"rewritten_files": 4}}
URL = f"/v1/table-maintenance-runs/{RUN_ID}/result"
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


def test_get_run_is_flat() -> None:
    """Getting a run returns its one operation, parameters and timeline at the top level."""
    stub = StubUseCase(GetTableMaintenanceRunUseCaseOutput(**FIELDS))
    client = build_client(get_table_maintenance_run=stub)

    response = client.get(f"/v1/table-maintenance-runs/{RUN_ID}")

    body = response.json()
    assert response.status_code == 200
    assert body["operation"] == "rewrite_data_files"
    assert "operations" not in body
    assert body["execution_ref"] == "wf-run-1"
    assert body["priority"] == "P1"
    assert body["started_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert body["settings"] == {"target_file_size_bytes": 536870912}
    assert body["partitions"] == []
    assert body["skip_reason"] is None
    assert [a["job_name"] for a in body["attempts"]] == [
        f"{RUN_ID}-rewrite_data_files-1",
        f"{RUN_ID}-rewrite_data_files-2",
    ]
    assert stub.requests == [GetTableMaintenanceRunUseCaseInput(run_id=RUN_ID)]


def test_run_response_lists_each_attempt() -> None:
    """A run lists every attempt with its job, size, failure class and what followed it."""
    client = build_client(get_table_maintenance_run=StubUseCase(GetTableMaintenanceRunUseCaseOutput(**FIELDS)))

    attempts = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()["attempts"]

    assert attempts[1]["size"] == "M"
    assert attempts[0] == {
        "attempt": 1,
        "size": "S",
        "status": "failed",
        "job_name": f"{RUN_ID}-rewrite_data_files-1",
        "started_at": NOW.isoformat().replace("+00:00", "Z"),
        "started_running_at": NOW.isoformat().replace("+00:00", "Z"),
        "finished_at": NOW.isoformat().replace("+00:00", "Z"),
        "failure_class": "oom",
        "error": "java.lang.OutOfMemoryError: Java heap space",
        "event_log_finished": False,
        "next_step": "retry_larger",
        "next_size": "M",
    }


def test_a_fresh_attempt_is_queued_and_has_not_started_running() -> None:
    """A run's fresh attempt reads queued, with no running time yet."""
    runs = InMemoryTableMaintenanceRunsRepo()
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_ID),
        TableId("u-1"),
        TriggerType.MANUAL,
        MaintenanceOperation.REWRITE_DATA_FILES,
        NOW,
        execution_ref="wf-run-1",
        content=RewriteDataFilesJobContent(target_file_size_bytes=1),
    )
    run.start_attempt(1, "job-1", NOW, size=ComputeSize.S)
    runs.create(run)
    client = build_client(get_table_maintenance_run=GetTableMaintenanceRunService(runs))

    body = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()

    assert body["status"] == "queued"
    assert body["attempts"][0]["status"] == "queued"
    assert body["attempts"][0]["started_running_at"] is None
    assert body["attempts"][0]["job_name"] == "job-1"


def test_a_pending_run_has_no_start() -> None:
    """A run that has only been created reads pending, with no start and no attempts."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=False)
    client = build_client(get_table_maintenance_run=GetTableMaintenanceRunService(runs))

    body = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()

    assert body["status"] == "pending"
    assert body["started_at"] is None
    assert body["attempts"] == []


DAY = PartitionFieldInfo(field_id=1000, name="ts_day", source_column="ts", source_type="timestamptz", transform="day")
OLD = PartitionFieldInfo(field_id=1001, name="old", source_column="old", source_type="string", transform="void")
EU = SpecPartitions(spec=PartitionSpecInfo(spec_id=0, fields=(DAY, OLD)), values=((20412, "x"), (None, None)))
EU_BODY = {
    "spec_id": 0,
    "fields": [{"column": "ts", "transform": "day"}],
    "partitions": [["2025-11-20"], [None]],
}


def _stored_run(runs: InMemoryTableMaintenanceRunsRepo, *, with_partitions: bool) -> None:
    runs.create(
        TableMaintenanceRun.create(
            TableMaintenanceRunId(RUN_ID),
            TableId("u-1"),
            TriggerType.SCHEDULED,
            MaintenanceOperation.REWRITE_DATA_FILES,
            NOW,
            execution_ref="wf-run-1",
            content=RewriteDataFilesJobContent(
                target_file_size_bytes=536870912, partitions=(EU,) if with_partitions else ()
            ),
        )
    )


def test_get_run_shows_the_partitions() -> None:
    """A compaction lists the partitions it rewrites per spec, values as Iceberg prints them, void fields left out."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=True)
    client = build_client(get_table_maintenance_run=GetTableMaintenanceRunService(runs))

    body = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()

    assert body["partitions"] == [EU_BODY]


def test_get_run_shows_no_partitions_for_the_whole_table() -> None:
    """A run stored without partitions shows an empty list."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=False)
    client = build_client(get_table_maintenance_run=GetTableMaintenanceRunService(runs))

    body = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()

    assert body["partitions"] == []


def test_get_run_shows_the_settings_and_the_skip_reason() -> None:
    """A skipped expire_snapshots run shows its settings, options beside them, and why it was skipped."""
    runs = InMemoryTableMaintenanceRunsRepo()
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_ID),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        NOW,
        execution_ref="wf-run-1",
        content=ExpireSnapshotsJobContent.from_primitives(
            {"older_than": "2026-10-23T08:00:00+08:00", "retain_last": 5, "options": {"stream_results": True}}
        ),
    )
    run.skip("the table's maintenance stopped before this run started", NOW)
    runs.create(run)
    client = build_client(get_table_maintenance_run=GetTableMaintenanceRunService(runs))

    body = client.get(f"/v1/table-maintenance-runs/{RUN_ID}").json()

    assert body["status"] == "skipped"
    assert body["settings"] == {"older_than": "2026-10-23T08:00:00+08:00", "retain_last": 5, "stream_results": True}
    assert body["skip_reason"] == "the table's maintenance stopped before this run started"
    assert body["error"] is None


def test_list_runs_of_a_table_shows_the_partitions() -> None:
    """The runs of a table list the partitions of their compaction."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=True)
    client = build_client(list_table_maintenance_runs=ListTableMaintenanceRunsService(runs))

    body = client.get("/v1/tables/u-1/table-maintenance-runs").json()

    assert body[0]["partitions"] == [EU_BODY]


def test_run_schema_types_its_partitions_and_attempts() -> None:
    """The OpenAPI schema names the partition and attempt shapes, and has no operation shape."""
    schemas = build_client().get("/openapi.json").json()["components"]["schemas"]

    properties = schemas["TableMaintenanceRunApiResponse"]["properties"]
    assert properties["attempts"]["items"] == {"$ref": "#/components/schemas/TableMaintenanceRunAttemptApiResponse"}
    assert properties["partitions"]["items"] == {
        "$ref": "#/components/schemas/TableMaintenanceRunPartitionSpecApiResponse"
    }
    assert "filters" not in properties
    assert "procedure_args" not in properties
    assert "operations" not in properties
    assert "TableMaintenanceRunOperationApiResponse" not in schemas


def test_callback_returns_202_and_maps_the_body() -> None:
    """The callback returns 202 and maps its body to the record result input."""
    stub = StubUseCase(ForwardTableMaintenanceResultUseCaseOutput(accepted=True))
    client = build_client(forward_table_maintenance_result=stub)

    response = client.post(URL, json=CALLBACK)

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert stub.requests == [
        ForwardTableMaintenanceResultUseCaseInput(
            run_id=RUN_ID,
            operation=None,
            attempt=1,
            succeeded=True,
            metrics={"rewritten_files": 4},
            error=None,
        )
    ]


def test_the_callback_needs_no_operation_in_its_path() -> None:
    """The result route is the run's own: its path names the run and the body may leave the operation out."""
    stub = StubUseCase(ForwardTableMaintenanceResultUseCaseOutput(accepted=True))
    client = build_client(forward_table_maintenance_result=stub)

    response = client.post(f"/v1/table-maintenance-runs/{RUN_ID}/result", json=CALLBACK)

    assert response.status_code == 202
    assert stub.requests[0].operation is None


def test_callback_accepts_the_runtime_body_with_matching_ids() -> None:
    """The callback accepts the body the Spark runtime sends when its ids match the path."""
    stub = StubUseCase(ForwardTableMaintenanceResultUseCaseOutput(accepted=True))
    client = build_client(forward_table_maintenance_result=stub)
    body = {
        **CALLBACK,
        "run_id": RUN_ID,
        "operation": "rewrite_data_files",
        "error": None,
        "extra_runtime_field": "ignored",
    }

    assert client.post(URL, json=body).status_code == 202
    assert stub.requests[0].operation == "rewrite_data_files"


def test_callback_body_run_id_mismatching_the_path_returns_422() -> None:
    """A callback body whose run id differs from the path is rejected with 422 and not recorded."""
    stub = StubUseCase(ForwardTableMaintenanceResultUseCaseOutput(accepted=True))
    client = build_client(forward_table_maintenance_result=stub)

    response = client.post(URL, json={**CALLBACK, "run_id": "other"})

    assert response.status_code == 422
    assert stub.requests == []


def _callback_service(runs: InMemoryTableMaintenanceRunsRepo) -> tuple[ForwardTableMaintenanceResultService, Any]:
    results = RecordingSendMaintenanceResultGateway()
    return ForwardTableMaintenanceResultService(runs, results), results


def test_the_callback_refuses_another_operation() -> None:
    """A body naming an operation other than the run's is rejected with 422 and sends nothing."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=False)
    service, results = _callback_service(runs)
    client = build_client(forward_table_maintenance_result=service)

    response = client.post(URL, json={**CALLBACK, "operation": "expire_snapshots"})

    assert response.status_code == 422
    assert results.calls == []


def test_the_callback_of_the_runs_own_operation_is_forwarded() -> None:
    """A body naming the run's own operation, or none, is forwarded to the run's execution."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=False)
    service, results = _callback_service(runs)
    client = build_client(forward_table_maintenance_result=service)

    named = client.post(URL, json={**CALLBACK, "operation": "rewrite_data_files"})
    unnamed = client.post(URL, json=CALLBACK)

    assert (named.status_code, unnamed.status_code) == (202, 202)
    assert [c.operation for c in results.calls] == ["rewrite_data_files", "rewrite_data_files"]


def test_callback_for_unknown_run_returns_404() -> None:
    """A callback for an unknown run returns 404."""
    service, _ = _callback_service(InMemoryTableMaintenanceRunsRepo())
    client = build_client(forward_table_maintenance_result=service)

    response = client.post(URL, json=CALLBACK)

    assert response.status_code == 404


def test_callback_with_unknown_operation_returns_422() -> None:
    """A callback body naming an unknown operation is rejected with 422."""
    runs = InMemoryTableMaintenanceRunsRepo()
    _stored_run(runs, with_partitions=False)
    service, results = _callback_service(runs)
    client = build_client(forward_table_maintenance_result=service)

    response = client.post(URL, json={**CALLBACK, "operation": "defragment"})

    assert response.status_code == 422
    assert results.calls == []


def test_the_old_callback_path_is_gone() -> None:
    """The callback path that named the operation returns 404."""
    client = build_client()

    old = f"/v1/table-maintenance-runs/{RUN_ID}/operations/rewrite_data_files/result"

    assert client.post(old, json=CALLBACK).status_code == 404


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
    service = ForwardTableMaintenanceResultService(InMemoryTableMaintenanceRunsRepo(), results)
    client = build_client(forward_table_maintenance_result=service)

    response = client.post(f"/v1/table-maintenance-runs/{OLD_UUID_RUN_ID}/result", json=CALLBACK)

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
        ("/v1/table-maintenance-runs/{run_id}/result", "post"),
    ],
)
def test_run_id_path_parameter_describes_its_shape(path: str, method: str) -> None:
    """The ``run_id`` parameter tells an API user the ``mr-`` shape, with no pattern of its own."""
    parameter = _path_parameter(path, method, "run_id")
    assert "`mr-`" in parameter["description"]
    assert "ADR 0011" in parameter["description"]
    assert "pattern" not in parameter["schema"]
