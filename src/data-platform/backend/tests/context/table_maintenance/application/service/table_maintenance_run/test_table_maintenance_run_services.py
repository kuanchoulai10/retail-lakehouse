"""Test the maintenance run lifecycle services."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
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
)
from context.table_maintenance.application.service.table_maintenance_run import (
    CreateTableMaintenanceRunService,
    GetTableMaintenanceRunService,
    ListTableMaintenanceRunsService,
    ProcessTableMaintenanceCallbackService,
    RecordTableMaintenanceOperationResultService,
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
        "operations": ("expire_snapshots", "rewrite_data_files"),
        "execution_ref": "wf-run-1",
        "now": now,
    }
    fields.update(overrides)
    return CreateTableMaintenanceRunUseCaseInput(**fields)


@pytest.fixture
def creator(runs_repo, tables_repo):
    """Provide the create run service on the fakes."""
    return CreateTableMaintenanceRunService(runs_repo, tables_repo)


def test_create_run_persists_pending_run_in_canonical_order(creator, runs_repo, table, now):
    """Creating a run stores it with its operations in canonical order and its execution reference."""
    out = creator.execute(_create_input(now))
    assert (out.run_id, out.table_uuid, out.trigger) == (RUN_1, "u-1", "scheduled")
    assert out.execution_ref == "wf-run-1"
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).execution_ref == "wf-run-1"
    assert out.status == "pending"
    assert [o["operation"] for o in out.operations] == [
        "rewrite_data_files",
        "expire_snapshots",
    ]
    assert out.operations[0]["status"] == "pending"
    assert out.created_at == now
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)) is not None


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


def test_create_run_with_an_unknown_priority_is_refused(creator, runs_repo, table, now):
    """A priority outside P0 to P3 raises a ValidationError and stores nothing."""
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, priority="P9"))
    assert len(runs_repo.items) == 0


def test_create_input_without_a_priority_parses_as_p3(now):
    """A payload written before runs had a priority still parses, as P3."""
    parsed = CreateTableMaintenanceRunUseCaseInput.from_primitives(
        {
            "run_id": RUN_1,
            "table_uuid": "u-1",
            "execution_ref": "wf-run-1",
            "trigger": "scheduled",
            "operations": ["rewrite_data_files"],
            "now": now.isoformat(),
        }
    )
    assert parsed.priority == "P3"


def test_create_run_is_idempotent_by_id(creator, runs_repo, table, now):
    """Creating a run twice with the same id returns the existing run."""
    creator.execute(_create_input(now))
    run = runs_repo.get(TableMaintenanceRunId(RUN_1))
    run.start_attempt(RDF, 1, "app-1", now)
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
        creator.execute(_create_input(now, operations=("defragment",)))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, operations=()))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, execution_ref=""))
    with pytest.raises(NotFoundError):
        creator.execute(_create_input(now, table_uuid="missing"))


# --- record result ---


@pytest.fixture
def started_run(runs_repo, table, now):
    """Provide a stored run whose first attempt has started."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_1),
        table.id,
        TriggerType.SCHEDULED,
        [RDF, OPS.EXPIRE_SNAPSHOTS],
        now,
        execution_ref="wf-run-1",
    )
    run.start_attempt(RDF, 1, "tm-rdf-run1-a1", now)
    runs_repo.create(run)
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
    """Recording a failure updates the run and the failure state of the table."""
    later = now + timedelta(minutes=5)
    out = _record(recorder, later, succeeded=False, error="OOM")
    assert (out.run_id, out.status) == (RUN_1, "running")
    op = started_run.operations[0]
    assert (op.status.value, op.error, op.finished_at) == ("failed", "OOM", later)
    state = table.operation_state(RDF)
    assert (state.consecutive_failures, state.last_attempt_at) == (1, later)


def test_record_success_stores_metrics_and_resets_backoff(recorder, started_run, table, now):
    """Recording a success stores the metrics and resets the failure count."""
    table.record_operation_result(RDF, False, now)
    _record(recorder, now)
    assert started_run.operations[0].metrics == {"rewritten_files": 4}
    assert table.operation_state(RDF).consecutive_failures == 0


def test_record_result_saves_run_then_table(recorder, started_run, table, runs_repo, tables_repo, log, now):
    """The run is saved before the table."""
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    _record(recorder, now)
    assert log == [("runs.update", RUN_1), ("tables.update", "u-1")]


def test_record_result_stale_attempt_is_ignored(recorder, started_run, table, now):
    """A result for a stale attempt changes neither the run nor the table."""
    started_run.fail(RDF, 1, "boom", now)
    started_run.start_attempt(RDF, 2, "tm-rdf-run1-a2", now)
    out = _record(recorder, now, attempt=1, succeeded=False, error="late")
    assert out.status == "queued"
    assert started_run.operations[0].status.value == "queued"
    assert table.operation_state(RDF).consecutive_failures == 0


def test_record_result_replay_does_not_count_twice(recorder, started_run, table, now):
    """Replaying a recorded result does not count the failure twice."""
    _record(recorder, now, succeeded=False, error="OOM")
    _record(recorder, now, succeeded=False, error="OOM")
    assert table.operation_state(RDF).consecutive_failures == 1


def test_record_result_failure_without_error_gets_a_default(recorder, started_run, table, now):
    """A failure without an error message gets a default message."""
    _record(recorder, now, succeeded=False, error=None)
    assert started_run.operations[0].error == "unknown error"


def test_record_result_for_dropped_table_still_updates_run(recorder, started_run, table, now):
    """A result for a dropped table still updates the run and leaves the table alone."""
    table.mark_dropped(now)
    out = _record(recorder, now)
    assert started_run.operations[0].status.value == "succeeded"
    assert out.status == "running"
    assert table.operation_states == {}


def test_record_result_final_operation_finishes_run(recorder, started_run, table, now):
    """Recording the result of the last operation finishes the run."""
    _record(recorder, now)
    started_run.start_attempt(OPS.EXPIRE_SNAPSHOTS, 1, "tm-es-run1-a1", now)
    out = _record(recorder, now, operation="expire_snapshots")
    assert out.status == "succeeded"


def test_record_result_rejects_bad_requests(recorder, started_run, now):
    """Requests for an unknown run, an invalid input or an operation outside the run are rejected."""
    with pytest.raises(NotFoundError):
        _record(recorder, now, run_id=UNKNOWN_RUN)
    with pytest.raises(ValidationError):
        _record(recorder, now, operation="defragment")
    with pytest.raises(ConflictError, match="not part of"):
        _record(recorder, now, operation="remove_orphan_files")
    with pytest.raises(ConflictError, match="never started"):
        _record(recorder, now, attempt=2)


# --- callback ---


def test_callback_forwards_result_to_the_workflow(runs_repo, started_run, results):
    """The callback forwards the result to the workflow and accepts it."""
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
    out = service.execute(
        ProcessTableMaintenanceCallbackUseCaseInput(
            run_id=RUN_1, operation="rewrite_data_files", attempt=3, succeeded=False, metrics={"a": 1}, error="OOM"
        )
    )
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
        service.execute(
            ProcessTableMaintenanceCallbackUseCaseInput(
                run_id=UNKNOWN_RUN, operation="rewrite_data_files", attempt=1, succeeded=True, metrics={}, error=None
            )
        )
    assert results.calls == []


def test_callback_rejects_unknown_operation(runs_repo, started_run, results):
    """A callback with an unknown operation raises a ValidationError."""
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
    with pytest.raises(ValidationError):
        service.execute(
            ProcessTableMaintenanceCallbackUseCaseInput(
                run_id=RUN_1, operation="x", attempt=1, succeeded=True, metrics={}, error=None
            )
        )


# --- get / list ---


def test_get_run_returns_the_run_or_not_found(runs_repo, started_run):
    """Getting a run returns it with its operations, or raises NotFoundError."""
    service = GetTableMaintenanceRunService(runs_repo)
    out = service.execute(GetTableMaintenanceRunUseCaseInput(run_id=RUN_1))
    assert out.status == "queued"
    assert out.operations[0]["job_name"] == "tm-rdf-run1-a1"
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
                [RDF],
                now + timedelta(minutes=i),
                execution_ref=f"wf-run-{i}",
            )
        )
    service = ListTableMaintenanceRunsService(runs_repo)
    out = service.execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1"))
    assert [i.run_id for i in out.items] == [RUN_2, RUN_1, numbered_id("mr", 0)]
    limited = service.execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="u-1", limit=1))
    assert [i.run_id for i in limited.items] == [RUN_2]
    assert service.execute(ListTableMaintenanceRunsUseCaseInput(table_uuid="other")).items == ()


def test_run_output_lists_every_attempt(runs_repo, started_run, now):
    """A run's output lists each attempt of an operation with its size and outcome as plain values."""
    started_run.fail(
        RDF,
        1,
        "java.lang.OutOfMemoryError",
        now,
        failure_class=FailureClass.OOM,
        event_log_finished=False,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    started_run.start_attempt(RDF, 2, "tm-rdf-run1-a2", now, size=ComputeSize.M)
    runs_repo.update(started_run)
    out = GetTableMaintenanceRunService(runs_repo).execute(GetTableMaintenanceRunUseCaseInput(run_id=RUN_1))
    rdf = next(op for op in out.operations if op["operation"] == "rewrite_data_files")
    assert rdf["attempt_history"] == [
        {
            "attempt": 1,
            "size": None,
            "status": "failed",
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
            "started_at": now,
            "started_running_at": None,
            "finished_at": None,
            "failure_class": None,
            "error": None,
            "event_log_finished": None,
            "next_step": None,
            "next_size": None,
        },
    ]


def _attention_mark(now) -> AttentionMark:
    return AttentionMark(
        since=now,
        reason="out of memory at size L",
        policy=AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None),
        policy_name=TableMaintenancePolicyName(value="default"),
    )


def test_manual_run_clears_needs_attention_of_its_operations(creator, tables_repo, table, now):
    """A new manual run lifts the needs-attention mark of its own operations only."""
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
