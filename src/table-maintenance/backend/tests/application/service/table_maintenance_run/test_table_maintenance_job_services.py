"""Test the submit, job status and job delete services."""

from __future__ import annotations


import pytest

from application.domain.model.table_discovery_rule import TableDiscoveryRuleId
from application.domain.model.shared import MaintenanceOperation, MaintenanceSettings
from application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from application.domain.model.table import Table, TableName, TableId
from application.domain.model.table_maintenance_preset import TableMaintenancePresetId
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table_maintenance_run import (
    DeleteMaintenanceJobUseCaseInput,
    GetMaintenanceJobStatusUseCaseInput,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseInputFilterItem,
    RecordTableMaintenanceOperationResultUseCaseInput,
)
from application.port.outbound.table_maintenance_run import (
    SubmitMaintenanceJobGatewayInput,
    SubmitMaintenanceJobGateway,
)
from application.service.table_maintenance_run import (
    DeleteMaintenanceJobService,
    GetMaintenanceJobStatusService,
    RecordTableMaintenanceOperationResultService,
    SubmitMaintenanceOperationService,
)
from tests.fakes.track_calls import track_calls

NAME = TableName("iceberg", "sales", "orders")
KEY = ("iceberg", "sales", "orders")
OPS = MaintenanceOperation


def _table(repo, now, settings=None, uuid="u-1", name=NAME):
    table = Table.register_auto(
        TableId(uuid),
        name,
        TableDiscoveryRuleId("r-1"),
        TableMaintenancePresetId("t-1"),
        settings or MaintenanceSettings(),
        now,
    )
    repo.create(table)
    return table


@pytest.fixture
def run(runs_repo, tables_repo, now):
    _table(tables_repo, now)
    created = TableMaintenanceRun.create(
        TableMaintenanceRunId("run-1"),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        [OPS.REWRITE_DATA_FILES, OPS.EXPIRE_SNAPSHOTS],
        now,
        execution_ref="wf-run-1",
    )
    runs_repo.create(created)
    return created


@pytest.fixture
def submitter(runs_repo, tables_repo, submit_job):
    return SubmitMaintenanceOperationService(runs_repo, tables_repo, submit_job)


def _filter(spec_id, where):
    return SubmitMaintenanceOperationUseCaseInputFilterItem(spec_id, where)


def _submit(submitter, now, **overrides):
    fields = {
        "run_id": "run-1",
        "operation": "rewrite_data_files",
        "attempt": 1,
        "filters": [
            SubmitMaintenanceOperationUseCaseInputFilterItem(0, "a = 1"),
            SubmitMaintenanceOperationUseCaseInputFilterItem(1, "b = 2"),
        ],
        "procedure_args": {"min-input-files": 2},
        "callback_base_url": "http://tm.example:8000/",
        "now": now,
    }
    fields.update(overrides)
    return submitter.execute(SubmitMaintenanceOperationUseCaseInput(**fields))


def test_submit_submits_job_then_records_attempt_with_its_job_name(
    submitter, run, submit_job, now
):
    out = _submit(submitter, now)
    assert out.job_name == "job-run-1-rewrite_data_files-1"
    job = submit_job.jobs[out.job_name]
    assert (job.run_id, job.operation, job.attempt) == (
        "run-1",
        "rewrite_data_files",
        1,
    )
    assert (job.catalog, job.namespace, job.table) == ("iceberg", "sales", "orders")
    assert job.where == ["a = 1", "b = 2"]
    assert job.procedure_args == {"min-input-files": 2}
    assert job.callback_url == (
        "http://tm.example:8000/v1/table-maintenance-runs/run-1"
        "/operations/rewrite_data_files/result"
    )
    op = run.operations[0]
    assert (op.attempts, op.job_name) == (1, out.job_name)


def test_submit_records_the_attempt_before_submitting_then_attaches_the_job(
    submitter, run, runs_repo, submit_job, log, now
):
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    track_calls(submit_job, "submit", "job.submit", log, lambda i: i.run_id)
    _submit(submitter, now)
    assert log == [
        ("runs.update", "run-1"),
        ("job.submit", "run-1"),
        ("runs.update", "run-1"),
    ]


def test_submit_never_calls_the_gateway_for_a_rejected_attempt(
    submitter, run, runs_repo, submit_job, now
):
    with pytest.raises(ConflictError):
        _submit(submitter, now, attempt=3)
    with pytest.raises(ConflictError):
        _submit(submitter, now, operation="remove_orphan_files")
    assert submit_job.calls == []
    assert runs_repo.get(TableMaintenanceRunId("run-1")).operations[0].attempts == 0


class _FailingSubmitGateway(SubmitMaintenanceJobGateway):
    def submit(self, input):  # noqa: A002
        raise RuntimeError("k8s down")


def test_failed_submit_can_be_recorded_and_the_next_attempt_goes_through(
    runs_repo, tables_repo, run, submit_job, now
):
    failing = SubmitMaintenanceOperationService(
        runs_repo, tables_repo, _FailingSubmitGateway()
    )
    with pytest.raises(RuntimeError, match="k8s down"):
        _submit(failing, now)
    recorder = RecordTableMaintenanceOperationResultService(runs_repo, tables_repo)
    recorder.execute(
        RecordTableMaintenanceOperationResultUseCaseInput(
            "run-1", "rewrite_data_files", 1, False, {}, "submit failed", now
        )
    )
    op = runs_repo.get(TableMaintenanceRunId("run-1")).operations[0]
    assert (op.status.value, op.attempts) == ("failed", 1)
    working = SubmitMaintenanceOperationService(runs_repo, tables_repo, submit_job)
    out = _submit(working, now, attempt=2)
    assert out.job_name == "job-run-1-rewrite_data_files-2"


def test_submit_whole_table_filter_means_no_where(submitter, run, submit_job, now):
    _submit(submitter, now, filters=[_filter(0, "")])
    assert next(iter(submit_job.jobs.values())).where == []


def test_submit_any_empty_where_makes_the_whole_table_the_target(
    submitter, run, submit_job, now
):
    _submit(submitter, now, filters=[_filter(0, "a = 1"), _filter(1, "")])
    assert next(iter(submit_job.jobs.values())).where == []


def test_retried_submit_leaves_one_job_and_records_the_attempt_once(
    submitter, run, submit_job, now
):
    first = _submit(submitter, now)
    second = _submit(submitter, now)
    assert first == second
    assert len(submit_job.calls) == 2
    assert len(submit_job.jobs) == 1
    op = run.operations[0]
    assert (op.attempts, op.job_name) == (1, first.job_name)


def test_retried_submit_after_a_lost_record_still_records_the_attempt(
    submitter, run, runs_repo, submit_job, now
):
    submit_job.submit(
        SubmitMaintenanceJobGatewayInput(
            run_id="run-1",
            operation="rewrite_data_files",
            attempt=1,
            catalog="iceberg",
            namespace="sales",
            table="orders",
            where=[],
            procedure_args={},
            callback_url="http://x",
        )
    )
    out = _submit(submitter, now)
    assert len(submit_job.jobs) == 1
    stored = runs_repo.get(TableMaintenanceRunId("run-1")).operations[0]
    assert (stored.attempts, stored.job_name) == (1, out.job_name)


def test_submit_next_attempt_uses_a_new_job_name(submitter, run, submit_job, now):
    _submit(submitter, now)
    run.fail(OPS.REWRITE_DATA_FILES, 1, "boom", now)
    out = _submit(submitter, now, attempt=2)
    assert out.job_name == "job-run-1-rewrite_data_files-2"
    assert len(submit_job.jobs) == 2


def test_submit_rejects_bad_requests(submitter, run, submit_job, tables_repo, now):
    with pytest.raises(NotFoundError):
        _submit(submitter, now, run_id="nope")
    with pytest.raises(ValidationError):
        _submit(submitter, now, operation="defragment")
    assert submit_job.calls == []
    del tables_repo.items["u-1"]
    with pytest.raises(NotFoundError):
        _submit(submitter, now)


# --- job status / delete ---


def _status_input(run_id="run-1", operation="rewrite_data_files", attempt=1):
    return GetMaintenanceJobStatusUseCaseInput(run_id, operation, attempt)


def test_get_job_status_passes_state_and_error_through(read_job):
    read_job.set_state("run-1", "rewrite_data_files", 1, "FAILED", "OOM")
    service = GetMaintenanceJobStatusService(read_job)
    out = service.execute(_status_input())
    assert (out.state, out.error) == ("FAILED", "OOM")
    missing = service.execute(_status_input(attempt=2))
    assert (missing.state, missing.error) == ("NOT_FOUND", None)
    assert [(c.run_id, c.operation, c.attempt) for c in read_job.calls] == [
        ("run-1", "rewrite_data_files", 1),
        ("run-1", "rewrite_data_files", 2),
    ]


def test_get_job_status_rejects_unknown_state(read_job):
    read_job.set_state("run-1", "rewrite_data_files", 1, "WEIRD")
    with pytest.raises(ValidationError):
        GetMaintenanceJobStatusService(read_job).execute(_status_input())


@pytest.mark.parametrize(
    ("operation", "attempt"), [("nope", 1), ("expire_snapshots", 0)]
)
def test_get_job_status_rejects_invalid_operation_or_attempt(
    read_job, operation, attempt
):
    with pytest.raises(ValidationError):
        GetMaintenanceJobStatusService(read_job).execute(
            _status_input(operation=operation, attempt=attempt)
        )
    assert read_job.calls == []


def test_delete_job_forwards_the_attempt_to_the_gateway(delete_job):
    out = DeleteMaintenanceJobService(delete_job).execute(
        DeleteMaintenanceJobUseCaseInput(
            run_id="run1", operation="rewrite_data_files", attempt=2
        )
    )
    assert (out.run_id, out.operation, out.attempt) == (
        "run1",
        "rewrite_data_files",
        2,
    )
    assert [(c.run_id, c.operation, c.attempt) for c in delete_job.calls] == [
        ("run1", "rewrite_data_files", 2)
    ]


@pytest.mark.parametrize(
    ("operation", "attempt"), [("nope", 1), ("expire_snapshots", 0)]
)
def test_delete_job_rejects_invalid_operation_or_attempt(
    delete_job, operation, attempt
):
    with pytest.raises(ValidationError):
        DeleteMaintenanceJobService(delete_job).execute(
            DeleteMaintenanceJobUseCaseInput(
                run_id="run1", operation=operation, attempt=attempt
            )
        )
    assert delete_job.calls == []
