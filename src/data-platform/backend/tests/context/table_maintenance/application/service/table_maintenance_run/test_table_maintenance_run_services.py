"""Test the maintenance run lifecycle services."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    SpecFilter,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    NextAttempt,
    NextStep,
    RunStatus,
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
    CreateTableMaintenanceRunUseCaseInput,
    GetTableMaintenanceRunUseCaseInput,
    ListTableMaintenanceRunsUseCaseInput,
    ProcessTableMaintenanceCallbackUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseInput,
    SkipTableMaintenanceRunUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    CreateTableMaintenanceRunService,
    GetTableMaintenanceRunService,
    ListTableMaintenanceRunsService,
    ProcessTableMaintenanceCallbackService,
    RecordTableMaintenanceOperationResultService,
    SkipTableMaintenanceRunService,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_event_log_gateway import (
    ScriptedReadMaintenanceEventLogGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_evidence_gateway import (
    ScriptedReadMaintenanceJobEvidenceGateway,
)
from tests.context.table_maintenance.fakes.track_calls import track_calls
from tests.context.table_maintenance.numbered_id import numbered_id

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
        TableDiscoveryRuleId.new(),
        now,
    )
    tables_repo.create(t)
    return t


def _create_input(now, run_id=RUN_1, **overrides):
    fields: dict[str, Any] = {
        "run_id": run_id,
        "table_uuid": "u-1",
        "trigger": "scheduled",
        "operation": "rewrite_data_files",
        "execution_ref": "wf-run-1",
        "now": now,
    }
    fields.update(overrides)
    return CreateTableMaintenanceRunUseCaseInput(**fields)


@pytest.fixture
def creator(runs_repo, tables_repo):
    """Provide the create run service on the fakes."""
    return CreateTableMaintenanceRunService(runs_repo, tables_repo)


def test_create_run_persists_a_pending_run(creator, runs_repo, table, now):
    """Creating a run stores it pending, with its operation and its execution reference."""
    out = creator.execute(_create_input(now))
    assert (out.run_id, out.table_uuid, out.trigger) == (RUN_1, "u-1", "scheduled")
    assert out.execution_ref == "wf-run-1"
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).execution_ref == "wf-run-1"
    assert (out.operation, out.status) == ("rewrite_data_files", "pending")
    assert (out.started_at, out.finished_at, out.attempts) == (None, None, ())
    assert out.created_at == now


def test_create_saves_one_operation_with_its_parameters(creator, runs_repo, table, now):
    """A run of expire_snapshots is stored with the arguments its procedure is called with."""
    out = creator.execute(_create_input(now, operation="expire_snapshots", procedure_args={"retain_last": 1}))
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1))
    assert stored.operation is OPS.EXPIRE_SNAPSHOTS
    assert stored.procedure_args == {"retain_last": 1}
    assert stored.status is RunStatus.PENDING
    assert out.procedure_args == {"retain_last": 1}


def test_create_run_records_its_priority(creator, runs_repo, table, now):
    """A run created with a priority stores it and reports it."""
    out = creator.execute(_create_input(now, priority="P0"))
    assert out.priority == "P0"
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P0


def test_create_run_without_a_priority_records_p3(creator, runs_repo, table, now):
    """A run created without a priority records P3."""
    out = creator.execute(_create_input(now))
    assert out.priority == "P3"
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P3


def test_create_run_service_saves_the_filters(creator, runs_repo, table, now):
    """The where clauses of a compaction are stored on the run and reported."""
    out = creator.execute(
        _create_input(now, filters=(CreateTableMaintenanceRunUseCaseInput.Filter(spec_id=0, where="x"),))
    )
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1))
    assert stored.filters == (SpecFilter(spec_id=0, where="x"),)
    assert out.filters == ({"spec_id": 0, "where": "x"},)


def test_create_refuses_an_unknown_operation(creator, runs_repo, table, now):
    """An operation that does not exist raises a ValidationError and stores nothing."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, operation="compact"))
    assert len(runs_repo.items) == 0


def test_create_refuses_filters_on_expire(creator, runs_repo, table, now):
    """Filters on a run other than rewrite_data_files raise a ConflictError and store nothing."""
    with pytest.raises(ConflictError):
        creator.execute(
            _create_input(
                now,
                operation="expire_snapshots",
                filters=(CreateTableMaintenanceRunUseCaseInput.Filter(spec_id=0, where="x"),),
            )
        )
    assert len(runs_repo.items) == 0


def test_create_run_with_an_unknown_priority_is_refused(creator, runs_repo, table, now):
    """A priority outside P0 to P3 raises a ValidationError and stores nothing."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, priority="P9"))
    assert len(runs_repo.items) == 0


def test_create_input_without_a_priority_parses_as_p3(now):
    """A payload without a priority, filters or arguments parses, as P3 on the whole table with no arguments."""
    parsed = CreateTableMaintenanceRunUseCaseInput.from_primitives(
        {
            "run_id": RUN_1,
            "table_uuid": "u-1",
            "execution_ref": "wf-run-1",
            "trigger": "scheduled",
            "operation": "rewrite_data_files",
            "now": now.isoformat(),
        }
    )
    assert (parsed.priority, parsed.filters, parsed.procedure_args) == ("P3", (), {})


def test_create_run_is_idempotent_by_id(creator, runs_repo, table, now):
    """Creating a run twice with the same id returns the existing run."""
    creator.execute(_create_input(now))
    run = runs_repo.get(TableMaintenanceRunId(RUN_1))
    run.start_attempt(1, "app-1", now, size=ComputeSize.S)
    again = creator.execute(_create_input(now + timedelta(hours=1), trigger="manual"))
    assert again.trigger == "scheduled"
    assert again.status == "queued"
    assert again.created_at == now
    assert len(runs_repo.items) == 1


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
def recorder(runs_repo, tables_repo, resolve_applicable_policy):
    """Provide the record operation result service on the fakes."""
    return RecordTableMaintenanceOperationResultService(
        runs_repo,
        tables_repo,
        ScriptedReadMaintenanceJobEvidenceGateway(),
        ScriptedReadMaintenanceEventLogGateway(),
        resolve_applicable_policy,
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
    }
    fields.update(overrides)
    return recorder.execute(RecordTableMaintenanceOperationResultUseCaseInput(**fields))


def test_record_result_updates_run_and_table_backoff(recorder, started_run, table, now):
    """Recording a failure fails the run and updates the failure state of the table."""
    later = now + timedelta(minutes=5)
    out = _record(recorder, later, succeeded=False, error="OOM")
    assert (out.run_id, out.status) == (RUN_1, "failed")
    assert (started_run.status, started_run.error, started_run.finished_at) == (RunStatus.FAILED, "OOM", later)
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
    assert started_run.status is RunStatus.QUEUED
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
    assert started_run.status is RunStatus.SUCCEEDED
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


# --- callback ---


def _callback(**overrides) -> ProcessTableMaintenanceCallbackUseCaseInput:
    fields: dict[str, Any] = {
        "run_id": RUN_1,
        "operation": "rewrite_data_files",
        "attempt": 3,
        "succeeded": False,
        "metrics": {"a": 1},
        "error": "OOM",
    }
    fields.update(overrides)
    return ProcessTableMaintenanceCallbackUseCaseInput(**fields)


def test_callback_forwards_result_to_the_workflow(runs_repo, started_run, results):
    """The callback forwards the result to the workflow and accepts it."""
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
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
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
    with pytest.raises(NotFoundError):
        service.execute(_callback(run_id=UNKNOWN_RUN))
    assert results.calls == []


def test_callback_rejects_unknown_operation(runs_repo, started_run, results):
    """A callback with an unknown operation raises a ValidationError."""
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
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
    assert (stored.status, stored.skip_reason) == (RunStatus.SKIPPED, SKIP_REASON)
    assert stored.finished_at == now + timedelta(minutes=1)


def test_skip_leaves_a_started_run_alone(runs_repo, started_run, log, now):
    """A run that started is not skipped, not saved, and says so."""
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    out = _skip(runs_repo, now)
    assert log == []
    assert (out.status, out.skipped) == ("queued", False)
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).status is RunStatus.QUEUED


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
