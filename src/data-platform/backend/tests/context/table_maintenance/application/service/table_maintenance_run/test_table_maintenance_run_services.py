"""Test the maintenance run lifecycle services."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TableId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import AppliedPolicyRef, AttentionMark, Table, TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    ExpireSnapshotsJobContent,
    FailureClass,
    NextAttempt,
    NextStep,
    RunStatusName,
    TableMaintenanceRun,
    TriggerType,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunsUseCaseInput,
    ForwardTableMaintenanceResultUseCaseInput,
    GetTableMaintenanceRunUseCaseInput,
    ListTableMaintenanceRunsUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseInput,
    SkipTableMaintenanceRunUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    CreateTableMaintenanceRunsService,
    ForwardTableMaintenanceResultService,
    GetTableMaintenanceRunService,
    ListTableMaintenanceRunsService,
    RecordTableMaintenanceOperationResultService,
    SkipTableMaintenanceRunService,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.job_content import job_content
from tests.context.table_maintenance.fakes.scripted_read_maintenance_event_log_gateway import (
    ScriptedReadMaintenanceEventLogGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_evidence_gateway import (
    ScriptedReadMaintenanceJobEvidenceGateway,
)
from tests.context.table_maintenance.fakes.track_calls import track_calls
from tests.context.table_maintenance.numbered_id import numbered_id
from tests.context.table_maintenance.planned_record_fields import PLANNED_RECORD_FIELDS

RUN_1 = "mr-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"
UNKNOWN_RUN = "mr-7zzzzzzzzzzzzzzzzzzzzzzzzz"

OPS = MaintenanceOperation
RDF = OPS.REWRITE_DATA_FILES
SKIP_REASON = "the table's maintenance stopped before this run started"


@pytest.fixture
def table(tables_repo, now):
    """Provide a stored active table."""
    t = Table.register(
        TableId("u-1"),
        TableName(catalog="iceberg", namespace="sales", table="orders"),
        MANAGED,
        now,
    )
    tables_repo.create(t)
    return t


def _planned_run(run_id, operation, content=None):
    """Plan one run of ``operation``, with ``content`` or the default content of its operation."""
    if content is None:
        known = operation in {op.value for op in MaintenanceOperation}
        content = job_content(MaintenanceOperation(operation)).to_primitives() if known else {"operation": operation}
    return CreateTableMaintenanceRunsUseCaseInput.Run(run_id=run_id, operation=operation, content=content)


EXPIRY = {"operation": "expire_snapshots", "older_than": "2026-10-23T08:00:00+08:00", "retain_last": 1}


def _create_input(now, *, runs=None, operation="rewrite_data_files", content=None, **overrides):
    """Build the request to create the runs of one plan: run 1 of ``operation`` by default, or ``runs``."""
    one = _planned_run(RUN_1, operation, content)
    fields: dict[str, Any] = {
        "table_uuid": "u-1",
        "trigger": "scheduled",
        "execution_ref": "wf-run-1",
        "now": now,
        "runs": (one,) if runs is None else runs,
        "priority": "P3",
    }
    fields.update(overrides)
    return CreateTableMaintenanceRunsUseCaseInput(**fields)


@pytest.fixture
def creator(runs_repo, tables_repo):
    """Provide the create runs service on the fakes."""
    return CreateTableMaintenanceRunsService(runs_repo, tables_repo)


def test_create_run_persists_a_pending_run(creator, runs_repo, table, now):
    """Creating a run stores it pending, with its operation and its execution reference."""
    out = creator.execute(_create_input(now))
    assert out.run_ids == (RUN_1,)
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1))
    assert (stored.table_uuid, stored.trigger, stored.execution_ref) == (
        TableId("u-1"),
        TriggerType.SCHEDULED,
        "wf-run-1",
    )
    assert (stored.operation, stored.status) == (RDF, RunStatusName.PENDING)
    assert (stored.started_at, stored.finished_at, stored.attempts) == (None, None, ())
    assert stored.created_at == now


def test_create_stores_every_run_of_the_plan_at_one_time(creator, runs_repo, table, now):
    """The runs of a plan are stored together, pending, each with its own operation, all created at ``now``."""
    out = creator.execute(
        _create_input(
            now,
            runs=(
                _planned_run(RUN_1, "rewrite_data_files"),
                _planned_run(RUN_2, "expire_snapshots", EXPIRY),
            ),
        )
    )
    assert out.run_ids == (RUN_1, RUN_2)
    first, second = (runs_repo.get(TableMaintenanceRunId(r)) for r in (RUN_1, RUN_2))
    assert (first.operation, second.operation) == (RDF, OPS.EXPIRE_SNAPSHOTS)
    assert {first.status, second.status} == {RunStatusName.PENDING}
    assert first.created_at == second.created_at == now
    assert second.content == ExpireSnapshotsJobContent.from_primitives(EXPIRY)


def test_create_saves_one_operation_with_its_content(creator, runs_repo, table, now):
    """A run of expire_snapshots is stored with the job content the plan built for it."""
    creator.execute(_create_input(now, operation="expire_snapshots", content=EXPIRY))
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1))
    assert stored.operation is OPS.EXPIRE_SNAPSHOTS
    assert stored.content == ExpireSnapshotsJobContent.from_primitives(EXPIRY)
    assert stored.status is RunStatusName.PENDING


def test_create_run_records_its_priority(creator, runs_repo, table, now):
    """Runs created with a priority store it."""
    creator.execute(_create_input(now, priority="P0"))
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P0


def test_create_run_records_the_priority_it_names(creator, runs_repo, table, now):
    """Runs are created at the priority the request names."""
    creator.execute(_create_input(now, priority="P1"))
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P1


def test_create_refuses_content_it_cannot_read(creator, runs_repo, table, now):
    """Content without a known operation raises a ValidationError and stores nothing."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, content={"operation": "compact"}))
    assert len(runs_repo.items) == 0


def test_create_refuses_an_unknown_operation(creator, runs_repo, table, now):
    """An operation that does not exist raises a ValidationError and stores nothing."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, operation="compact"))
    assert len(runs_repo.items) == 0


def test_create_refuses_content_of_another_operation(creator, runs_repo, table, now):
    """An expire_snapshots run holding compaction content raises a ConflictError and stores nothing."""
    with pytest.raises(ConflictError):
        creator.execute(
            _create_input(
                now,
                operation="expire_snapshots",
                content=job_content(MaintenanceOperation.REWRITE_DATA_FILES).to_primitives(),
            )
        )
    assert len(runs_repo.items) == 0


def test_create_stores_no_run_of_the_plan_when_one_is_refused(creator, runs_repo, table, now):
    """A plan whose second run is refused stores neither run: the plan's runs are created all or none."""
    refused = _planned_run(
        RUN_2, "expire_snapshots", job_content(MaintenanceOperation.REWRITE_DATA_FILES).to_primitives()
    )
    with pytest.raises(ConflictError):
        creator.execute(_create_input(now, runs=(_planned_run(RUN_1, "rewrite_data_files"), refused)))
    assert len(runs_repo.items) == 0


def test_create_stores_the_plans_runs_in_one_batch(creator, runs_repo, table, now):
    """The plan's runs go to the repository in one batch, so a run it cannot store leaves every run unstored."""
    batches: list[list[str]] = []

    def refuse(runs):
        batches.append([r.id.value for r in runs])
        raise ConflictError("the database refused the batch")

    runs_repo.create_all = refuse
    plan = (_planned_run(RUN_1, "rewrite_data_files"), _planned_run(RUN_2, "expire_snapshots"))
    with pytest.raises(ConflictError):
        creator.execute(_create_input(now, runs=plan))
    assert batches == [[RUN_1, RUN_2]]
    assert len(runs_repo.items) == 0


def test_create_run_with_an_unknown_priority_is_refused(creator, runs_repo, table, now):
    """A priority outside P0 to P3 raises a ValidationError and stores nothing."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, priority="P9"))
    assert len(runs_repo.items) == 0


def test_create_input_requires_the_content_of_each_run(now):
    """A planned run without content is refused: the plan always builds what the job does."""
    with pytest.raises(InvariantViolation, match="content"):
        CreateTableMaintenanceRunsUseCaseInput.from_primitives(
            {
                "table_uuid": "u-1",
                "execution_ref": "wf-run-1",
                "trigger": "scheduled",
                "now": now.isoformat(),
                "priority": "P3",
                "runs": [{"run_id": RUN_1, "operation": "rewrite_data_files"}],
            }
        )


def test_create_input_requires_a_priority(now):
    """A payload without a priority is refused: the plan always names the table's priority."""
    with pytest.raises(InvariantViolation, match="priority"):
        CreateTableMaintenanceRunsUseCaseInput.from_primitives(
            {
                "table_uuid": "u-1",
                "execution_ref": "wf-run-1",
                "trigger": "scheduled",
                "now": now.isoformat(),
                "runs": [{"run_id": RUN_1, "operation": "expire_snapshots", "content": EXPIRY}],
            }
        )


def test_create_run_is_idempotent_by_id(creator, runs_repo, table, now):
    """Creating the runs of a plan again returns their ids and leaves the stored runs as they are."""
    creator.execute(_create_input(now))
    run = runs_repo.get(TableMaintenanceRunId(RUN_1))
    run.start_attempt(1, "app-1", now, size=ComputeSize.S)
    again = creator.execute(_create_input(now + timedelta(hours=1), trigger="manual"))
    assert again.run_ids == (RUN_1,)
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1))
    assert (stored.trigger, stored.status, stored.created_at) == (TriggerType.SCHEDULED, RunStatusName.QUEUED, now)
    assert len(runs_repo.items) == 1


def _two_run_plan():
    return (_planned_run(RUN_1, "rewrite_data_files"), _planned_run(RUN_2, "expire_snapshots"))


def test_a_create_retried_after_its_first_try_stored_the_plan_returns_the_stored_runs(creator, runs_repo, table, now):
    """A retry of a create that already stored every run of the plan succeeds, returns their ids and stores nothing."""
    creator.execute(_create_input(now, runs=_two_run_plan()))
    batches: list[int] = []
    runs_repo.create_all = lambda runs: batches.append(len(runs))
    again = creator.execute(_create_input(now, runs=_two_run_plan()))
    assert again.run_ids == (RUN_1, RUN_2)
    assert batches == []
    assert sorted(runs_repo.items) == [RUN_1, RUN_2]


def _first_try_lands_during_the_insert(runs_repo, first_try) -> None:
    """Make another try's insert land between this try's reads and its insert, as a slow first try racing its retry."""
    insert = runs_repo.create_all

    def raced(runs):
        runs_repo.create_all = insert
        first_try()
        return insert(runs)

    runs_repo.create_all = raced


def test_a_retry_whose_insert_meets_the_first_tries_runs_returns_them(creator, runs_repo, tables_repo, table, now):
    """A retry that read no run but whose insert hits the runs its first try stored meanwhile returns those runs."""
    first = CreateTableMaintenanceRunsService(runs_repo, tables_repo)
    _first_try_lands_during_the_insert(runs_repo, lambda: first.execute(_create_input(now, runs=_two_run_plan())))
    out = creator.execute(_create_input(now, runs=_two_run_plan()))
    assert out.run_ids == (RUN_1, RUN_2)
    assert sorted(runs_repo.items) == [RUN_1, RUN_2]


def test_an_insert_that_meets_runs_not_stored_as_planned_is_a_conflict(creator, runs_repo, tables_repo, table, now):
    """An insert that hits a run id stored meanwhile for another operation is the real conflict."""
    other = CreateTableMaintenanceRunsService(runs_repo, tables_repo)
    _first_try_lands_during_the_insert(
        runs_repo, lambda: other.execute(_create_input(now, operation="expire_snapshots"))
    )
    with pytest.raises(ConflictError):
        creator.execute(_create_input(now, runs=_two_run_plan()))
    assert runs_repo.get(TableMaintenanceRunId(RUN_2)) is None


def test_a_create_whose_plan_is_only_partly_stored_is_a_conflict(creator, runs_repo, table, now):
    """A plan with some of its run ids stored and others not is refused, and the missing runs are not stored."""
    creator.execute(_create_input(now))
    with pytest.raises(ConflictError):
        creator.execute(_create_input(now, runs=_two_run_plan()))
    assert runs_repo.get(TableMaintenanceRunId(RUN_2)) is None


def test_a_create_whose_run_id_is_stored_for_another_operation_is_a_conflict(creator, runs_repo, table, now):
    """A run id already stored for another operation is refused instead of being taken as this plan's run."""
    creator.execute(_create_input(now, operation="expire_snapshots"))
    with pytest.raises(ConflictError):
        creator.execute(_create_input(now))


def test_a_create_whose_run_id_is_stored_for_another_table_is_a_conflict(creator, runs_repo, tables_repo, table, now):
    """A run id already stored for another table is refused instead of being taken as this plan's run."""
    creator.execute(_create_input(now))
    with pytest.raises(ConflictError):
        creator.execute(_create_input(now, table_uuid="u-2"))


def test_create_run_validates_input(creator, table, now):
    """Invalid run input raises a ValidationError."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, trigger="whenever"))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, operation="defragment"))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, execution_ref=""))
    with pytest.raises(NotFoundError):
        creator.execute(_create_input(now, table_uuid="missing"))


# --- record result ---


def _stored_run(runs_repo, table, now, run_id=RUN_1, operation=RDF) -> TableMaintenanceRun:
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(run_id),
        table.id,
        TriggerType.SCHEDULED,
        operation,
        now,
        content=job_content(operation),
        execution_ref="wf-run-1",
    )
    runs_repo.create(run)
    return run


@pytest.fixture
def started_run(runs_repo, table, now):
    """Provide a stored compaction run whose first attempt has started."""
    run = _stored_run(runs_repo, table, now)
    run.start_attempt(1, "tm-rdf-run1-a1", now, size=ComputeSize.S)
    return run


@pytest.fixture
def recorder(runs_repo, tables_repo):
    """Provide the record operation result service on the fakes."""
    return RecordTableMaintenanceOperationResultService(
        runs_repo,
        tables_repo,
        ScriptedReadMaintenanceJobEvidenceGateway(),
        ScriptedReadMaintenanceEventLogGateway(),
        size_memory={},
    )


def _record(recorder, now, **overrides):
    fields: dict[str, Any] = {
        "run_id": RUN_1,
        "operation": "rewrite_data_files",
        "attempt": 1,
        "succeeded": True,
        "metrics": {"rewritten_files": 4},
        "error": None,
        "now": now,
        **PLANNED_RECORD_FIELDS,
    }
    fields.update(overrides)
    return recorder.execute(RecordTableMaintenanceOperationResultUseCaseInput(**fields))


def test_record_result_updates_run_and_table_backoff(recorder, started_run, table, now):
    """Recording a failure fails the run and updates the failure state of the table."""
    later = now + timedelta(minutes=5)
    out = _record(recorder, later, succeeded=False, error="OOM")
    assert (out.run_id, out.status) == (RUN_1, "failed")
    assert (started_run.status, started_run.error, started_run.finished_at) == (RunStatusName.FAILED, "OOM", later)
    state = table.operation_state(RDF)
    assert (state.consecutive_failures, state.last_attempt_at) == (1, later)


def test_record_success_stores_metrics_and_resets_backoff(recorder, started_run, table, now):
    """Recording a success finishes the run with the metrics and resets the failure count."""
    table.record_operation_result(RDF, False, now)
    out = _record(recorder, now)
    assert out.status == "succeeded"
    assert started_run.metrics == {"rewritten_files": 4}
    assert table.operation_state(RDF).consecutive_failures == 0


def test_record_result_saves_run_then_table(recorder, started_run, table, runs_repo, tables_repo, log, now):
    """The run is saved before the table."""
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    _record(recorder, now)
    assert log == [("runs.update", RUN_1), ("tables.update", "u-1")]


def test_record_result_stale_attempt_is_ignored(recorder, started_run, table, now):
    """A result for a stale attempt changes neither the run nor the table."""
    started_run.fail(1, "boom", now)
    started_run.start_attempt(2, "tm-rdf-run1-a2", now, size=ComputeSize.S)
    out = _record(recorder, now, attempt=1, succeeded=False, error="late")
    assert out.status == "queued"
    assert started_run.status is RunStatusName.QUEUED
    assert table.operation_state(RDF).consecutive_failures == 0


def test_record_result_replay_does_not_count_twice(recorder, started_run, table, now):
    """Replaying a recorded result does not count the failure twice."""
    _record(recorder, now, succeeded=False, error="OOM")
    _record(recorder, now, succeeded=False, error="OOM")
    assert table.operation_state(RDF).consecutive_failures == 1


def test_record_result_failure_without_error_gets_a_default(recorder, started_run, table, now):
    """A failure without an error message gets a default message."""
    _record(recorder, now, succeeded=False, error=None)
    assert started_run.error == "unknown error"


def test_record_result_for_dropped_table_still_updates_run(recorder, started_run, table, now):
    """A result for a dropped table still updates the run and leaves the table alone."""
    table.mark_dropped(now)
    out = _record(recorder, now)
    assert started_run.status is RunStatusName.SUCCEEDED
    assert out.status == "succeeded"
    assert table.operation_states == {}


def test_record_result_rejects_bad_requests(recorder, started_run, now):
    """Requests for an unknown run, an invalid input, another operation or an unstarted attempt are rejected."""
    with pytest.raises(NotFoundError):
        _record(recorder, now, run_id=UNKNOWN_RUN)
    with pytest.raises(ValidationError):
        _record(recorder, now, operation="defragment")
    with pytest.raises(ConflictError, match="does not run remove_orphan_files"):
        _record(recorder, now, operation="remove_orphan_files")
    with pytest.raises(ConflictError, match="never started"):
        _record(recorder, now, attempt=2)


def test_recording_an_attempt_of_a_run_still_pending_changes_nothing(recorder, runs_repo, tables_repo, table, now):
    """A run whose first submit never started its attempt is still pending: the record answers so and saves nothing.

    The workflow records a failure for every attempt it began, also one a cancel or a refused submit stopped before
    the submit saved the attempt; that is not a failed record, so it is neither refused nor saved.
    """
    _stored_run(runs_repo, table, now)
    saves: list[tuple[str, str]] = []
    track_calls(runs_repo, "update", "run", saves, lambda r: r.id.value)
    track_calls(tables_repo, "update", "table", saves, lambda t: t.id.value)
    out = _record(recorder, now, attempt=1, succeeded=False, error="cancelled", ended_by="cancelled")
    assert (out.status, out.failure_class, out.next_step) == ("pending", None, None)
    assert saves == []
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).status is RunStatusName.PENDING


# --- callback ---


def _callback(**overrides) -> ForwardTableMaintenanceResultUseCaseInput:
    fields: dict[str, Any] = {
        "run_id": RUN_1,
        "operation": "rewrite_data_files",
        "attempt": 3,
        "succeeded": False,
        "metrics": {"a": 1},
        "error": "OOM",
    }
    fields.update(overrides)
    return ForwardTableMaintenanceResultUseCaseInput(**fields)


def test_callback_forwards_result_to_the_workflow(runs_repo, started_run, results):
    """The callback forwards the result to the workflow and accepts it."""
    service = ForwardTableMaintenanceResultService(runs_repo, results)
    out = service.execute(_callback())
    assert out.accepted is True
    (call,) = results.calls
    assert (call.run_id, call.operation, call.attempt) == (
        RUN_1,
        "rewrite_data_files",
        3,
    )
    assert (call.succeeded, call.metrics, call.error) == (False, {"a": 1}, "OOM")
    assert call.execution_ref == "wf-run-1"


def test_callback_unknown_run_not_found(runs_repo, results):
    """A callback for an unknown run raises NotFoundError and forwards nothing."""
    service = ForwardTableMaintenanceResultService(runs_repo, results)
    with pytest.raises(NotFoundError):
        service.execute(_callback(run_id=UNKNOWN_RUN))
    assert results.calls == []


def test_callback_rejects_unknown_operation(runs_repo, started_run, results):
    """A callback with an unknown operation raises a ValidationError."""
    service = ForwardTableMaintenanceResultService(runs_repo, results)
    with pytest.raises(ValidationError):
        service.execute(_callback(operation="x"))
    assert results.calls == []


# --- get / list ---


def test_get_run_returns_the_run_or_not_found(runs_repo, started_run, now):
    """Getting a run returns its flat fields, or raises NotFoundError."""
    service = GetTableMaintenanceRunService(runs_repo)
    out = service.execute(GetTableMaintenanceRunUseCaseInput(run_id=RUN_1))
    assert (out.operation, out.status, out.started_at) == ("rewrite_data_files", "queued", now)
    assert out.attempts[0]["job_name"] == "tm-rdf-run1-a1"
    assert (out.metrics, out.error, out.skip_reason) == ({}, None, None)
    with pytest.raises(NotFoundError):
        service.execute(GetTableMaintenanceRunUseCaseInput(run_id=UNKNOWN_RUN))


def test_list_runs_newest_first_with_limit(runs_repo, table, now):
    """Listing runs of a table returns the newest first, cut at the limit."""
    for i in range(3):
        runs_repo.create(
            TableMaintenanceRun.create(
                TableMaintenanceRunId(numbered_id("mr", i)),
                table.id,
                TriggerType.MANUAL,
                RDF,
                now + timedelta(minutes=i),
                content=job_content(RDF),
                execution_ref=f"wf-run-{i}",
            )
        )
    service = ListTableMaintenanceRunsService(runs_repo)
    out = service.execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1"))
    assert [i.run_id for i in out.items] == [RUN_2, RUN_1, numbered_id("mr", 0)]
    assert out.items[0].operation == "rewrite_data_files"
    limited = service.execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1", limit=1))
    assert [i.run_id for i in limited.items] == [RUN_2]
    assert service.execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="other")).items == ()


def test_list_shows_runs_created_together_last_operation_first(runs_repo, table, now):
    """The runs a plan created at one time list its last operation first."""
    _stored_run(runs_repo, table, now, RUN_1, RDF)
    _stored_run(runs_repo, table, now, RUN_2, OPS.EXPIRE_SNAPSHOTS)
    out = ListTableMaintenanceRunsService(runs_repo).execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1"))
    assert [(i.run_id, i.operation) for i in out.items] == [(RUN_2, "expire_snapshots"), (RUN_1, "rewrite_data_files")]


def test_list_orders_runs_created_together_by_operation_before_id(runs_repo, table, now):
    """Among runs of one creation time the plan's operation order outranks the ids."""
    _stored_run(runs_repo, table, now, RUN_2, RDF)
    _stored_run(runs_repo, table, now, RUN_1, OPS.REMOVE_ORPHAN_FILES)
    out = ListTableMaintenanceRunsService(runs_repo).execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1"))
    assert [i.operation for i in out.items] == ["remove_orphan_files", "rewrite_data_files"]


def test_run_output_lists_every_attempt(runs_repo, started_run, now):
    """A run's output lists each attempt with its job, size and outcome as plain values."""
    started_run.fail(
        1,
        "java.lang.OutOfMemoryError",
        now,
        failure_class=FailureClass.OOM,
        event_log_finished=False,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    started_run.start_attempt(2, "tm-rdf-run1-a2", now, size=ComputeSize.M)
    runs_repo.update(started_run)
    out = GetTableMaintenanceRunService(runs_repo).execute(GetTableMaintenanceRunUseCaseInput(run_id=RUN_1))
    assert out.attempts == (
        {
            "attempt": 1,
            "size": "S",
            "status": "failed",
            "job_name": "tm-rdf-run1-a1",
            "started_at": now,
            "started_running_at": None,
            "finished_at": now,
            "failure_class": "oom",
            "error": "java.lang.OutOfMemoryError",
            "event_log_finished": False,
            "next_step": "retry_larger",
            "next_size": "M",
        },
        {
            "attempt": 2,
            "size": "M",
            "status": "queued",
            "job_name": "tm-rdf-run1-a2",
            "started_at": now,
            "started_running_at": None,
            "finished_at": None,
            "failure_class": None,
            "error": None,
            "event_log_finished": None,
            "next_step": None,
            "next_size": None,
        },
    )


# --- skip ---


def _skip(runs_repo, now, run_id=RUN_1):
    return SkipTableMaintenanceRunService(runs_repo).execute(
        SkipTableMaintenanceRunUseCaseInput(run_id=run_id, reason=SKIP_REASON, now=now)
    )


def test_skip_skips_a_pending_run(runs_repo, table, log, now):
    """A pending run is skipped, keeps why, and is saved once."""
    _stored_run(runs_repo, table, now)
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    out = _skip(runs_repo, now + timedelta(minutes=1))
    assert log == [("runs.update", RUN_1)]
    assert (out.run_id, out.status, out.skipped) == (RUN_1, "skipped", True)
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1))
    assert (stored.status, stored.skip_reason) == (RunStatusName.SKIPPED, SKIP_REASON)
    assert stored.finished_at == now + timedelta(minutes=1)


def test_skip_leaves_a_started_run_alone(runs_repo, started_run, log, now):
    """A run that started is not skipped, not saved, and says so."""
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    out = _skip(runs_repo, now)
    assert log == []
    assert (out.status, out.skipped) == ("queued", False)
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).status is RunStatusName.QUEUED


def test_skip_repeated_leaves_the_skipped_run_alone(runs_repo, table, log, now):
    """Skipping a run already skipped changes nothing, saves nothing and does not fail."""
    _stored_run(runs_repo, table, now)
    _skip(runs_repo, now)
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    out = _skip(runs_repo, now + timedelta(minutes=5))
    assert log == []
    assert (out.status, out.skipped) == ("skipped", False)
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).finished_at == now


def test_skip_of_an_unknown_run_is_not_found(runs_repo, now):
    """Skipping a run that does not exist raises NotFoundError."""
    with pytest.raises(NotFoundError):
        _skip(runs_repo, now, run_id=UNKNOWN_RUN)


def _attention_mark(now) -> AttentionMark:
    return AttentionMark(
        since=now,
        reason="out of memory at size L",
        policy=AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None),
        policy_name=TableMaintenancePolicyName(value="default"),
    )


def test_manual_run_clears_needs_attention_of_its_operation(creator, tables_repo, table, now):
    """A new manual run lifts the needs-attention mark of its own operation only."""
    table.mark_needs_attention(RDF, _attention_mark(now), now)
    table.mark_needs_attention(OPS.REMOVE_ORPHAN_FILES, _attention_mark(now), now)
    tables_repo.update(table)
    creator.execute(_create_input(now, trigger="manual"))
    stored = tables_repo.get(TableId("u-1"))
    assert stored.operation_state(RDF).attention is None
    assert stored.operation_state(OPS.REMOVE_ORPHAN_FILES).attention is not None


def test_a_manual_plan_clears_needs_attention_of_every_planned_operation(creator, tables_repo, table, now):
    """A manual plan of two runs lifts the needs-attention marks of both operations and leaves the others."""
    for op in (RDF, OPS.EXPIRE_SNAPSHOTS, OPS.REMOVE_ORPHAN_FILES):
        table.mark_needs_attention(op, _attention_mark(now), now)
    tables_repo.update(table)
    plan = (_planned_run(RUN_1, "rewrite_data_files"), _planned_run(RUN_2, "expire_snapshots"))
    creator.execute(_create_input(now, runs=plan, trigger="manual"))
    stored = tables_repo.get(TableId("u-1"))
    assert stored.operation_state(RDF).attention is None
    assert stored.operation_state(OPS.EXPIRE_SNAPSHOTS).attention is None
    assert stored.operation_state(OPS.REMOVE_ORPHAN_FILES).attention is not None


def test_scheduled_run_keeps_needs_attention(creator, tables_repo, table, now):
    """A scheduled run lifts no needs-attention mark."""
    table.mark_needs_attention(RDF, _attention_mark(now), now)
    tables_repo.update(table)
    creator.execute(_create_input(now))
    assert tables_repo.get(TableId("u-1")).operation_state(RDF).attention is not None


def test_recreating_a_manual_run_saves_no_table(creator, tables_repo, table, now):
    """Creating an existing manual run again changes no table."""
    creator.execute(_create_input(now, trigger="manual"))
    table.mark_needs_attention(RDF, _attention_mark(now), now)
    tables_repo.update(table)
    calls: list[tuple[str, str]] = []
    track_calls(tables_repo, "update", "table", calls, lambda t: t.id.value)
    creator.execute(_create_input(now, trigger="manual"))
    assert calls == []
    assert tables_repo.get(TableId("u-1")).operation_state(RDF).attention is not None
