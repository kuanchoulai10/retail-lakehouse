"""Test the submit, job status and job delete services."""

from __future__ import annotations

import copy
import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    DeleteMaintenanceJobUseCaseInput,
    GetMaintenanceJobStatusUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseInput,
    SubmitMaintenanceOperationUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SubmitMaintenanceJobGateway,
    SubmitMaintenanceJobGatewayInput,
    SubmitMaintenanceJobGatewayOutput,
    TableMaintenanceRunsRepo,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    DeleteMaintenanceJobService,
    GetMaintenanceJobStatusService,
    RecordTableMaintenanceOperationResultService,
    SubmitMaintenanceOperationService,
)
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_runs_repo import (
    InMemoryTableMaintenanceRunsRepo,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_event_log_gateway import (
    ScriptedReadMaintenanceEventLogGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_evidence_gateway import (
    ScriptedReadMaintenanceJobEvidenceGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_pods_gateway import (
    ScriptedReadMaintenanceJobPodsGateway,
)
from tests.context.table_maintenance.fakes.track_calls import track_calls

RUN_1 = "mr-00000000000000000000000001"
UNKNOWN_RUN = "mr-7zzzzzzzzzzzzzzzzzzzzzzzzz"

NAME = TableName(catalog="iceberg", namespace="sales", table="orders")
KEY = ("iceberg", "sales", "orders")
OPS = MaintenanceOperation


def _table(repo, now, settings=None, uuid="u-1", name=NAME):
    table = Table.register(TableId(uuid), name, TableDiscoveryRuleId.new(), now)
    repo.create(table)
    return table


@pytest.fixture
def run(runs_repo, tables_repo, now):
    """Provide a stored run with a rewrite data files operation."""
    _table(tables_repo, now)
    created = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_1),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        [OPS.REWRITE_DATA_FILES, OPS.EXPIRE_SNAPSHOTS],
        now,
        execution_ref="wf-run-1",
    )
    runs_repo.create(created)
    return created


@pytest.fixture
def submitter(runs_repo, tables_repo, submit_job, candidates_repo):
    """Provide the submit maintenance operation service on the fakes."""
    return SubmitMaintenanceOperationService(runs_repo, tables_repo, submit_job, candidates_repo=candidates_repo)


def _filter(spec_id, where):
    return SubmitMaintenanceOperationUseCaseInput.Filter(spec_id=spec_id, where=where)


def _submit(submitter, now, **overrides):
    fields: dict[str, Any] = {
        "run_id": RUN_1,
        "operation": "rewrite_data_files",
        "attempt": 1,
        "filters": (
            SubmitMaintenanceOperationUseCaseInput.Filter(spec_id=0, where="a = 1"),
            SubmitMaintenanceOperationUseCaseInput.Filter(spec_id=1, where="b = 2"),
        ),
        "procedure_args": {"min-input-files": 2},
        "callback_base_url": "http://tm.example:8000/",
        "now": now,
    }
    fields.update(overrides)
    return submitter.execute(SubmitMaintenanceOperationUseCaseInput(**fields))


def test_submit_submits_job_then_records_attempt_with_its_job_name(submitter, run, submit_job, now):
    """Submitting sends the job to the gateway and records the attempt with its job name."""
    out = _submit(submitter, now)
    assert out.job_name == f"job-{RUN_1}-rewrite_data_files-1"
    job = submit_job.jobs[out.job_name]
    assert (job.run_id, job.operation, job.attempt) == (
        RUN_1,
        "rewrite_data_files",
        1,
    )
    assert (job.catalog, job.namespace, job.table) == ("iceberg", "sales", "orders")
    assert job.where == ["a = 1", "b = 2"]
    assert job.procedure_args == {"min-input-files": 2}
    assert job.callback_url == (
        f"http://tm.example:8000/v1/table-maintenance-runs/{RUN_1}/operations/rewrite_data_files/result"
    )
    op = run.operations[0]
    assert (op.attempts, op.job_name) == (1, out.job_name)


def test_submit_records_the_attempt_before_submitting_then_attaches_the_job(
    submitter, run, runs_repo, submit_job, log, now
):
    """The attempt is recorded before the job is submitted and the job name is attached after."""
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    track_calls(submit_job, "submit", "job.submit", log, lambda i: i.run_id)
    _submit(submitter, now)
    assert log == [
        ("runs.update", RUN_1),
        ("job.submit", RUN_1),
        ("runs.update", RUN_1),
    ]


def test_submit_never_calls_the_gateway_for_a_rejected_attempt(submitter, run, runs_repo, submit_job, now):
    """A rejected attempt never reaches the gateway."""
    with pytest.raises(ConflictError):
        _submit(submitter, now, attempt=3)
    with pytest.raises(ConflictError):
        _submit(submitter, now, operation="remove_orphan_files")
    assert submit_job.calls == []
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).operations[0].attempts == 0


class _FailingSubmitGateway(SubmitMaintenanceJobGateway):
    def submit(self, input):  # noqa: A002
        raise RuntimeError("k8s down")


def test_failed_submit_can_be_recorded_and_the_next_attempt_goes_through(
    runs_repo, tables_repo, resolve_applicable_policy, run, submit_job, now
):
    """A failed submit can be recorded as failed and the next attempt is submitted."""
    failing = SubmitMaintenanceOperationService(
        runs_repo, tables_repo, _FailingSubmitGateway(), candidates_repo=InMemoryCompactionCandidatesRepo()
    )
    with pytest.raises(RuntimeError, match="k8s down"):
        _submit(failing, now)
    recorder = RecordTableMaintenanceOperationResultService(
        runs_repo,
        tables_repo,
        ScriptedReadMaintenanceJobEvidenceGateway(),
        ScriptedReadMaintenanceEventLogGateway(),
        resolve_applicable_policy,
        size_memory={},
        candidates_repo=InMemoryCompactionCandidatesRepo(),
    )
    recorder.execute(
        RecordTableMaintenanceOperationResultUseCaseInput(
            run_id=RUN_1,
            operation="rewrite_data_files",
            attempt=1,
            succeeded=False,
            metrics={},
            error="submit failed",
            now=now,
        )
    )
    op = runs_repo.get(TableMaintenanceRunId(RUN_1)).operations[0]
    assert (op.status.value, op.attempts) == ("failed", 1)
    working = SubmitMaintenanceOperationService(
        runs_repo, tables_repo, submit_job, candidates_repo=InMemoryCompactionCandidatesRepo()
    )
    out = _submit(working, now, attempt=2)
    assert out.job_name == f"job-{RUN_1}-rewrite_data_files-2"


def test_submit_whole_table_filter_means_no_where(submitter, run, submit_job, now):
    """A whole table filter submits the job without a where clause."""
    _submit(submitter, now, filters=(_filter(0, ""),))
    assert next(iter(submit_job.jobs.values())).where == []


def test_submit_any_empty_where_makes_the_whole_table_the_target(submitter, run, submit_job, now):
    """If any filter has an empty where clause the job targets the whole table."""
    _submit(submitter, now, filters=(_filter(0, "a = 1"), _filter(1, "")))
    assert next(iter(submit_job.jobs.values())).where == []


def test_retried_submit_leaves_one_job_and_records_the_attempt_once(submitter, run, submit_job, now):
    """A retried submit leaves one job and records the attempt once."""
    first = _submit(submitter, now)
    second = _submit(submitter, now)
    assert first == second
    assert len(submit_job.calls) == 2
    assert len(submit_job.jobs) == 1
    op = run.operations[0]
    assert (op.attempts, op.job_name) == (1, first.job_name)


def test_retried_submit_after_a_lost_record_still_records_the_attempt(submitter, run, runs_repo, submit_job, now):
    """A retried submit still records the attempt when the first record was lost."""
    submit_job.submit(
        SubmitMaintenanceJobGatewayInput(
            run_id=RUN_1,
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
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1)).operations[0]
    assert (stored.attempts, stored.job_name) == (1, out.job_name)


def test_submit_next_attempt_uses_a_new_job_name(submitter, run, submit_job, now):
    """The next attempt submits a job with a new name."""
    _submit(submitter, now)
    run.fail(OPS.REWRITE_DATA_FILES, 1, "boom", now)
    out = _submit(submitter, now, attempt=2)
    assert out.job_name == f"job-{RUN_1}-rewrite_data_files-2"
    assert len(submit_job.jobs) == 2


def test_submit_rejects_bad_requests(submitter, run, submit_job, tables_repo, now):
    """Requests for an unknown run or an invalid operation are rejected and not submitted."""
    with pytest.raises(NotFoundError):
        _submit(submitter, now, run_id=UNKNOWN_RUN)
    with pytest.raises(ValidationError):
        _submit(submitter, now, operation="defragment")
    assert submit_job.calls == []
    del tables_repo.items["u-1"]
    with pytest.raises(NotFoundError):
        _submit(submitter, now)


# --- job status / delete ---


def _status_input(run_id=RUN_1, operation="rewrite_data_files", attempt=1):
    return GetMaintenanceJobStatusUseCaseInput(run_id=run_id, operation=operation, attempt=attempt)


def test_get_job_status_passes_state_and_error_through(read_job):
    """The job status service passes the state and error of the gateway through."""
    read_job.set_state(RUN_1, "rewrite_data_files", 1, "FAILED", "OOM")
    service = GetMaintenanceJobStatusService(read_job, ScriptedReadMaintenanceJobPodsGateway())
    out = service.execute(_status_input())
    assert (out.state, out.error) == ("FAILED", "OOM")
    missing = service.execute(_status_input(attempt=2))
    assert (missing.state, missing.error) == ("NOT_FOUND", None)
    assert [(c.run_id, c.operation, c.attempt) for c in read_job.calls] == [
        (RUN_1, "rewrite_data_files", 1),
        (RUN_1, "rewrite_data_files", 2),
    ]


def test_get_job_status_rejects_unknown_state(read_job):
    """A job state the service does not know raises a ValidationError."""
    read_job.set_state(RUN_1, "rewrite_data_files", 1, "WEIRD")
    with pytest.raises(ValidationError):
        GetMaintenanceJobStatusService(read_job, ScriptedReadMaintenanceJobPodsGateway()).execute(_status_input())


@pytest.mark.parametrize(("operation", "attempt"), [("nope", 1), ("expire_snapshots", 0)])
def test_get_job_status_rejects_invalid_operation_or_attempt(read_job, operation, attempt):
    """An invalid operation or attempt is rejected before the gateway is called."""
    with pytest.raises(ValidationError):
        GetMaintenanceJobStatusService(read_job, ScriptedReadMaintenanceJobPodsGateway()).execute(
            _status_input(operation=operation, attempt=attempt)
        )
    assert read_job.calls == []


def test_job_status_reports_the_driver_start(read_job):
    """A job that exists reports when its driver started, read from the pods."""
    pods = ScriptedReadMaintenanceJobPodsGateway()
    started = datetime(2026, 11, 20, 3, 0, 5, tzinfo=UTC)
    read_job.set_state(RUN_1, "rewrite_data_files", 1, "RUNNING")
    pods.set_driver_started_at(RUN_1, "rewrite_data_files", 1, started.isoformat())

    out = GetMaintenanceJobStatusService(read_job, pods).execute(_status_input())

    assert (out.state, out.driver_started_at) == ("RUNNING", started)
    assert [(c.run_id, c.operation, c.attempt) for c in pods.calls] == [(RUN_1, "rewrite_data_files", 1)]


def test_job_status_without_a_started_driver_has_no_driver_start(read_job):
    """A job whose driver has not started reports no driver start."""
    read_job.set_state(RUN_1, "rewrite_data_files", 1, "PENDING")

    out = GetMaintenanceJobStatusService(read_job, ScriptedReadMaintenanceJobPodsGateway()).execute(_status_input())

    assert (out.state, out.driver_started_at) == ("PENDING", None)


def test_job_status_of_a_missing_job_reads_no_pods(read_job):
    """A job that is gone reads no pods."""
    pods = ScriptedReadMaintenanceJobPodsGateway()

    out = GetMaintenanceJobStatusService(read_job, pods).execute(_status_input())

    assert (out.state, out.driver_started_at) == ("NOT_FOUND", None)
    assert pods.calls == []


def test_job_status_survives_a_failed_pods_read(read_job, caplog):
    """A pods read that fails keeps the state and leaves the driver start out, with a warning."""
    pods = ScriptedReadMaintenanceJobPodsGateway()
    pods.error = RuntimeError("k8s down")
    read_job.set_state(RUN_1, "rewrite_data_files", 1, "RUNNING")

    with caplog.at_level(logging.WARNING):
        out = GetMaintenanceJobStatusService(read_job, pods).execute(_status_input())

    assert (out.state, out.driver_started_at) == ("RUNNING", None)
    assert "k8s down" in caplog.text


def test_delete_job_forwards_the_attempt_to_the_gateway(delete_job):
    """Deleting a job forwards the run, operation and attempt to the gateway."""
    out = DeleteMaintenanceJobService(delete_job).execute(
        DeleteMaintenanceJobUseCaseInput(run_id=RUN_1, operation="rewrite_data_files", attempt=2)
    )
    assert (out.run_id, out.operation, out.attempt) == (
        RUN_1,
        "rewrite_data_files",
        2,
    )
    assert [(c.run_id, c.operation, c.attempt) for c in delete_job.calls] == [(RUN_1, "rewrite_data_files", 2)]


@pytest.mark.parametrize(("operation", "attempt"), [("nope", 1), ("expire_snapshots", 0)])
def test_delete_job_rejects_invalid_operation_or_attempt(delete_job, operation, attempt):
    """An invalid operation or attempt is rejected before the gateway is called."""
    with pytest.raises(ValidationError):
        DeleteMaintenanceJobService(delete_job).execute(
            DeleteMaintenanceJobUseCaseInput(run_id=RUN_1, operation=operation, attempt=attempt)
        )
    assert delete_job.calls == []


class _CopyingRunsRepo(TableMaintenanceRunsRepo):
    """Hand out and store copies, like a SQL repo that overwrites the row."""

    def __init__(self):
        self.inner = InMemoryTableMaintenanceRunsRepo()

    def create(self, entity):
        return self.inner.create(copy.deepcopy(entity))

    def get(self, entity_id):
        stored = self.inner.get(entity_id)
        return None if stored is None else copy.deepcopy(stored)

    def list_all(self):
        return [copy.deepcopy(r) for r in self.inner.list_all()]

    def update(self, run):
        return self.inner.update(copy.deepcopy(run))

    def list_by_table(self, table_uuid, limit=50):
        return [copy.deepcopy(r) for r in self.inner.list_by_table(table_uuid, limit)]

    def list_by_table_since(self, table_uuid, since):
        return [copy.deepcopy(r) for r in self.inner.list_by_table_since(table_uuid, since)]


class _CancelDuringSubmitGateway(SubmitMaintenanceJobGateway):
    """Record the attempt as failed while the submit is still running."""

    def __init__(self, recorder, now):
        self.recorder = recorder
        self.now = now

    def submit(self, input):  # noqa: A002
        self.recorder.execute(
            RecordTableMaintenanceOperationResultUseCaseInput(
                run_id=input.run_id,
                operation=input.operation,
                attempt=input.attempt,
                succeeded=False,
                metrics={},
                error="cancelled",
                now=self.now,
            )
        )
        return SubmitMaintenanceJobGatewayOutput(job_name="job-cancelled")


def test_submit_does_not_overwrite_a_run_cancelled_during_the_submit(tables_repo, resolve_applicable_policy, now):
    """A run recorded as failed during the submit is not overwritten when the job name is attached."""
    runs_repo = _CopyingRunsRepo()
    _table(tables_repo, now)
    runs_repo.create(
        TableMaintenanceRun.create(
            TableMaintenanceRunId(RUN_1),
            TableId("u-1"),
            TriggerType.SCHEDULED,
            [OPS.REWRITE_DATA_FILES],
            now,
            execution_ref="wf-run-1",
        )
    )
    recorder = RecordTableMaintenanceOperationResultService(
        runs_repo,
        tables_repo,
        ScriptedReadMaintenanceJobEvidenceGateway(),
        ScriptedReadMaintenanceEventLogGateway(),
        resolve_applicable_policy,
        size_memory={},
        candidates_repo=InMemoryCompactionCandidatesRepo(),
    )
    submitter = SubmitMaintenanceOperationService(
        runs_repo,
        tables_repo,
        _CancelDuringSubmitGateway(recorder, now),
        candidates_repo=InMemoryCompactionCandidatesRepo(),
    )
    out = _submit(submitter, now)
    assert out.job_name == "job-cancelled"
    op = runs_repo.get(TableMaintenanceRunId(RUN_1)).operations[0]
    assert (op.status.value, op.attempts, op.job_name) == ("failed", 1, None)


def test_submit_records_the_attempt_size(submitter, run, runs_repo, submit_job, now):
    """The attempt is recorded at its size and the job is submitted at it."""
    out = _submit(submitter, now, size="M")
    assert submit_job.jobs[out.job_name].size == "M"
    record = runs_repo.get(TableMaintenanceRunId(RUN_1)).attempt_record(MaintenanceOperation.REWRITE_DATA_FILES, 1)
    assert record is not None
    assert record.size is ComputeSize.M


def test_submit_without_a_size_runs_at_s(submitter, run, submit_job, now):
    """A request without a size runs at S."""
    out = _submit(submitter, now)
    assert submit_job.jobs[out.job_name].size == "S"


def test_submit_refuses_an_unknown_size(submitter, run, runs_repo, submit_job, now):
    """A size outside S, M and L is refused before anything is recorded or submitted."""
    with pytest.raises(ValidationError, match="XL"):
        _submit(submitter, now, size="XL")
    assert submit_job.jobs == {}
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).operations[0].attempts == 0


def test_submit_passes_the_runs_priority(submitter, runs_repo, tables_repo, submit_job, now):
    """The job is submitted with the priority the run was created with."""
    _table(tables_repo, now)
    runs_repo.create(
        TableMaintenanceRun.create(
            TableMaintenanceRunId(RUN_1),
            TableId("u-1"),
            TriggerType.MANUAL,
            [OPS.REWRITE_DATA_FILES],
            now,
            execution_ref="wf-run-1",
            priority=TablePriority.P1,
        )
    )
    out = _submit(submitter, now)
    assert submit_job.jobs[out.job_name].priority == "P1"


def test_submit_of_a_default_run_is_p3(submitter, run, submit_job, now):
    """A run created without a priority is submitted as P3."""
    out = _submit(submitter, now)
    assert submit_job.jobs[out.job_name].priority == "P3"
