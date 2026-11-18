"""Tests for the TableMaintenanceRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    InvalidRunTransition,
    NextAttempt,
    NextStep,
    OperationAttempt,
    OperationRun,
    OperationRunStatus,
    RunStatus,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)

T0 = datetime(2026, 10, 24, tzinfo=UTC)


def _now(minutes: int = 0) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _run(ops: list[Op] | None = None) -> TableMaintenanceRun:
    return TableMaintenanceRun.create(
        TableMaintenanceRunId("run-1"),
        TableId("t-1"),
        TriggerType.MANUAL,
        ops if ops is not None else [Op.EXPIRE_SNAPSHOTS, Op.REWRITE_DATA_FILES],
        _now(),
        execution_ref="wf-run-1",
    )


def _op(run: TableMaintenanceRun, op: Op):
    return next(o for o in run.operations if o.operation == op)


def test_create_orders_dedupes_and_starts_pending():
    """Creating a run orders and deduplicates its operations and starts them all pending."""
    run = _run([Op.EXPIRE_SNAPSHOTS, Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    assert [o.operation for o in run.operations] == [
        Op.REWRITE_DATA_FILES,
        Op.EXPIRE_SNAPSHOTS,
    ]
    assert all(o.status is OperationRunStatus.PENDING and o.attempts == 0 for o in run.operations)
    assert run.status is RunStatus.PENDING
    assert run.finished_at is None
    assert run.created_at == _now()


def test_create_without_operations_raises():
    """Creating a run without operations is rejected."""
    with pytest.raises(InvalidRunTransition):
        _run([])


def test_status_rollup():
    """The run status follows its operations from pending to running."""
    run = _run([Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    assert run.status is RunStatus.PENDING
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "app-1", _now(1))
    assert run.status is RunStatus.RUNNING
    run.succeed(Op.REWRITE_DATA_FILES, 1, {"files": 3}, _now(2))
    assert run.status is RunStatus.RUNNING
    assert run.finished_at is None
    run.start_attempt(Op.EXPIRE_SNAPSHOTS, 1, "app-2", _now(3))
    run.succeed(Op.EXPIRE_SNAPSHOTS, 1, {}, _now(4))
    assert run.status is RunStatus.SUCCEEDED
    assert run.finished_at == _now(4)


def test_status_partially_failed_and_failed():
    """The run is partially failed when some operations fail and failed when all do, and is then finished."""
    run = _run([Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a", _now(1))
    run.succeed(Op.REWRITE_DATA_FILES, 1, {}, _now(2))
    run.start_attempt(Op.EXPIRE_SNAPSHOTS, 1, "b", _now(3))
    run.fail(Op.EXPIRE_SNAPSHOTS, 1, "boom", _now(4))
    assert run.status is RunStatus.PARTIALLY_FAILED
    assert run.finished_at == _now(4)

    run = _run([Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    for i, op in enumerate(run.operations):
        run.start_attempt(op.operation, 1, f"x{i}", _now(1))
        run.fail(op.operation, 1, "boom", _now(2))
    assert run.status is RunStatus.FAILED


def test_all_skipped_is_succeeded_and_skipped_ignored():
    """Skipped operations do not count against the run, which succeeds when the others do."""
    run = _run([Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    run.skip(Op.REWRITE_DATA_FILES, "nothing to do", _now(1))
    assert run.status is RunStatus.RUNNING
    run.skip(Op.EXPIRE_SNAPSHOTS, "nothing to do", _now(2))
    assert run.status is RunStatus.SUCCEEDED
    assert run.finished_at == _now(2)
    assert _op(run, Op.EXPIRE_SNAPSHOTS).error == "nothing to do"

    run = _run([Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    run.skip(Op.REWRITE_DATA_FILES, "r", _now(1))
    run.start_attempt(Op.EXPIRE_SNAPSHOTS, 1, "a", _now(2))
    run.fail(Op.EXPIRE_SNAPSHOTS, 1, "boom", _now(3))
    assert run.status is RunStatus.FAILED


def test_skip_only_from_pending():
    """An operation can only be skipped while it is pending."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a", _now(1))
    with pytest.raises(InvalidRunTransition):
        run.skip(Op.REWRITE_DATA_FILES, "r", _now(2))


def test_stale_attempt_result_ignored():
    """A result for an earlier attempt does not change the current attempt."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a1", _now(1))
    run.fail(Op.REWRITE_DATA_FILES, 1, "boom", _now(2))
    run.start_attempt(Op.REWRITE_DATA_FILES, 2, "a2", _now(3))
    run.succeed(Op.REWRITE_DATA_FILES, 1, {"x": 1}, _now(4))
    run.fail(Op.REWRITE_DATA_FILES, 1, "late", _now(4))
    op = _op(run, Op.REWRITE_DATA_FILES)
    assert op.status is OperationRunStatus.RUNNING
    assert op.attempts == 2
    assert op.job_name == "a2"


def test_retry_clears_previous_outcome():
    """Starting a new attempt clears the error, finish time and metrics of the previous one."""
    run = _run([Op.REWRITE_DATA_FILES])
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a1", _now(1))
    run.fail(Op.REWRITE_DATA_FILES, 1, "boom", _now(2))
    assert run.finished_at == _now(2)
    run.start_attempt(Op.REWRITE_DATA_FILES, 2, "a2", _now(3))
    op = _op(run, Op.REWRITE_DATA_FILES)
    assert op.error is None and op.finished_at is None and op.metrics == {}
    assert op.started_at == _now(3)
    assert run.finished_at is None
    assert run.status is RunStatus.RUNNING


def test_start_attempt_idempotent_and_guarded():
    """Starting the same attempt twice changes nothing and invalid attempt numbers are rejected."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a1", _now(1))
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a1", _now(2))
    assert _op(run, Op.REWRITE_DATA_FILES).started_at == _now(1)
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.REWRITE_DATA_FILES, 1, "other", _now(2))
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.REWRITE_DATA_FILES, 3, "a3", _now(2))
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.REWRITE_DATA_FILES, 2, "a2", _now(2))
    run.succeed(Op.REWRITE_DATA_FILES, 1, {}, _now(3))
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.REWRITE_DATA_FILES, 2, "a2", _now(4))


def test_duplicate_result_is_idempotent():
    """Recording the same success twice keeps the first result."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a", _now(1))
    metrics = {"files": 2}
    run.succeed(Op.REWRITE_DATA_FILES, 1, metrics, _now(2))
    metrics["files"] = 99
    run.succeed(Op.REWRITE_DATA_FILES, 1, {"files": 5}, _now(3))
    op = _op(run, Op.REWRITE_DATA_FILES)
    assert op.status is OperationRunStatus.SUCCEEDED
    assert op.metrics == {"files": 2}
    assert op.finished_at == _now(2)
    with pytest.raises(InvalidRunTransition):
        run.fail(Op.REWRITE_DATA_FILES, 1, "boom", _now(4))


def test_duplicate_fail_idempotent_and_succeed_after_fail_raises():
    """Recording the same failure twice keeps it, but a success after a failure is rejected."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a", _now(1))
    run.fail(Op.REWRITE_DATA_FILES, 1, "boom", _now(2))
    run.fail(Op.REWRITE_DATA_FILES, 1, "boom2", _now(3))
    assert _op(run, Op.REWRITE_DATA_FILES).error == "boom"
    with pytest.raises(InvalidRunTransition):
        run.succeed(Op.REWRITE_DATA_FILES, 1, {}, _now(4))


def test_result_for_future_or_unstarted_attempt_raises():
    """A result for a future or not yet started attempt is rejected."""
    run = _run()
    with pytest.raises(InvalidRunTransition):
        run.succeed(Op.REWRITE_DATA_FILES, 1, {}, _now(1))
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "a", _now(1))
    with pytest.raises(InvalidRunTransition):
        run.fail(Op.REWRITE_DATA_FILES, 2, "x", _now(2))


def test_unknown_operation_raises():
    """An operation that is not part of the run is rejected."""
    run = _run([Op.REWRITE_DATA_FILES])
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.REMOVE_ORPHAN_FILES, 1, "a", _now(1))
    with pytest.raises(InvalidRunTransition):
        run.skip(Op.REMOVE_ORPHAN_FILES, "r", _now(1))


def test_create_records_the_workflow_id():
    """A new run records the execution reference of its workflow."""
    assert _run().execution_ref == "wf-run-1"


def test_create_rejects_an_empty_execution_ref():
    """A run without an execution reference is rejected."""
    with pytest.raises(ValueError, match="execution reference"):
        TableMaintenanceRun.create(
            TableMaintenanceRunId("run-1"),
            TableId("t-1"),
            TriggerType.MANUAL,
            [Op.EXPIRE_SNAPSHOTS],
            _now(),
            execution_ref="",
        )


def test_start_attempt_without_a_job_name_then_attach_it():
    """An attempt can start without a job name and get it attached afterwards."""
    run = _run([Op.REWRITE_DATA_FILES])
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, None, _now(1))
    assert _op(run, Op.REWRITE_DATA_FILES).job_name is None
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, None, _now(2))
    run.attach_job_name(Op.REWRITE_DATA_FILES, 1, "j1")
    run.attach_job_name(Op.REWRITE_DATA_FILES, 1, "j1")
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, None, _now(3))
    op = _op(run, Op.REWRITE_DATA_FILES)
    assert (op.attempts, op.job_name, op.started_at) == (1, "j1", _now(1))


def test_attach_job_name_is_guarded():
    """Attaching a job name is rejected for an invalid attempt or operation."""
    run = _run([Op.REWRITE_DATA_FILES])
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(Op.REWRITE_DATA_FILES, 1, "j1")
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, None, _now(1))
    run.attach_job_name(Op.REWRITE_DATA_FILES, 1, "j1")
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(Op.REWRITE_DATA_FILES, 1, "other")
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(Op.REWRITE_DATA_FILES, 2, "j2")
    run.succeed(Op.REWRITE_DATA_FILES, 1, {}, _now(2))
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(Op.REWRITE_DATA_FILES, 1, "j1")


def test_forbidden_transition_still_raises_invalid_run_transition():
    """A forbidden transition raises InvalidRunTransition, not an InvariantViolation."""
    run = _run([Op.EXPIRE_SNAPSHOTS])
    with pytest.raises(InvalidRunTransition):
        run.succeed(Op.EXPIRE_SNAPSHOTS, 1, {}, _now(1))
    assert issubclass(InvalidRunTransition, ValueError)


def test_operation_update_revalidates():
    """Changing an operation goes through validation and rejects a wrong type."""
    operation = OperationRun(operation=Op.EXPIRE_SNAPSHOTS)
    with pytest.raises(InvariantViolation):
        operation.with_changes(attempts="many")


def test_operation_run_is_immutable():
    """An operation run cannot be changed in place."""
    operation = OperationRun(operation=Op.EXPIRE_SNAPSHOTS)
    with pytest.raises(AttributeError, match="is immutable"):
        operation.attempts = 3


def test_run_rejects_a_wrong_typed_assignment():
    """Assigning a wrong type to a run field raises InvariantViolation."""
    run = _run()
    with pytest.raises(InvariantViolation):
        run.created_at = "yesterday"  # ty: ignore[invalid-assignment]


def test_failed_state_change_leaves_the_run_unchanged():
    """A rejected transition leaves the operations as they were."""
    run = _run([Op.EXPIRE_SNAPSHOTS])
    before = run.model_dump()
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.EXPIRE_SNAPSHOTS, 5, None, _now(1))
    assert run.model_dump() == before


def _attempts(run: TableMaintenanceRun, op: Op = Op.REWRITE_DATA_FILES) -> tuple[OperationAttempt, ...]:
    return _op(run, op).attempt_history


def test_start_attempt_appends_a_running_attempt_with_its_size():
    """Starting an attempt records it as running at its size."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1), size=ComputeSize.M)
    assert _attempts(run) == (
        OperationAttempt(attempt=1, size=ComputeSize.M, status=OperationRunStatus.RUNNING, started_at=_now(1)),
    )


def test_restarting_the_running_attempt_adds_no_entry():
    """Starting the running attempt again leaves its one entry."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, None, _now(1), size=ComputeSize.S)
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(2), size=ComputeSize.S)
    assert len(_attempts(run)) == 1
    assert _attempts(run)[0].started_at == _now(1)


def test_fail_records_class_error_event_log_and_next_step_on_the_attempt():
    """A failure records its class, raw error, event log state and next step on its attempt."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(
        Op.REWRITE_DATA_FILES,
        1,
        "java.lang.OutOfMemoryError: Java heap space",
        _now(5),
        failure_class=FailureClass.OOM,
        event_log_finished=False,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    assert run.attempt_record(Op.REWRITE_DATA_FILES, 1) == OperationAttempt(
        attempt=1,
        size=ComputeSize.S,
        status=OperationRunStatus.FAILED,
        started_at=_now(1),
        finished_at=_now(5),
        failure_class=FailureClass.OOM,
        error="java.lang.OutOfMemoryError: Java heap space",
        event_log_finished=False,
        next_step=NextStep.RETRY_LARGER,
        next_size=ComputeSize.M,
    )
    assert _op(run, Op.REWRITE_DATA_FILES).error == "java.lang.OutOfMemoryError: Java heap space"


def test_fail_without_a_class_records_other():
    """A failure recorded without a class is other, with no next step."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1))
    run.fail(Op.REWRITE_DATA_FILES, 1, "boom", _now(2))
    record = run.attempt_record(Op.REWRITE_DATA_FILES, 1)
    assert record is not None
    assert record.failure_class is FailureClass.OTHER
    assert record.next_step is None


def test_succeed_marks_the_attempt_done():
    """A success marks its attempt succeeded with next step done."""
    run = _run()
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1), size=ComputeSize.M)
    run.succeed(Op.REWRITE_DATA_FILES, 1, {"rewritten_data_files_count": 3}, _now(4), event_log_finished=True)
    record = run.attempt_record(Op.REWRITE_DATA_FILES, 1)
    assert record is not None
    assert record.status is OperationRunStatus.SUCCEEDED
    assert record.finished_at == _now(4)
    assert record.event_log_finished is True
    assert record.next_step is NextStep.DONE
    assert record.next_size is None
    assert record.failure_class is None


def test_three_attempts_keep_three_entries():
    """S fails, M fails, L succeeds: three entries, oldest first."""
    run = _run([Op.REWRITE_DATA_FILES])
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(
        Op.REWRITE_DATA_FILES,
        1,
        "oom",
        _now(2),
        failure_class=FailureClass.OOM,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    run.start_attempt(Op.REWRITE_DATA_FILES, 2, "job-2", _now(3), size=ComputeSize.M)
    run.fail(
        Op.REWRITE_DATA_FILES,
        2,
        "oom",
        _now(4),
        failure_class=FailureClass.OOM,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.L),
    )
    run.start_attempt(Op.REWRITE_DATA_FILES, 3, "job-3", _now(5), size=ComputeSize.L)
    run.succeed(Op.REWRITE_DATA_FILES, 3, {}, _now(6))
    history = _attempts(run)
    assert [(a.attempt, a.size, a.status, a.next_step, a.next_size) for a in history] == [
        (1, ComputeSize.S, OperationRunStatus.FAILED, NextStep.RETRY_LARGER, ComputeSize.M),
        (2, ComputeSize.M, OperationRunStatus.FAILED, NextStep.RETRY_LARGER, ComputeSize.L),
        (3, ComputeSize.L, OperationRunStatus.SUCCEEDED, NextStep.DONE, None),
    ]
    assert _op(run, Op.REWRITE_DATA_FILES).attempts == 3
    assert _op(run, Op.REWRITE_DATA_FILES).error is None


def test_finishing_an_attempt_started_before_attempt_history_adds_its_entry():
    """An attempt started before attempt history existed gets its entry when it finishes."""
    run = _run([Op.REWRITE_DATA_FILES])
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1))
    legacy = _op(run, Op.REWRITE_DATA_FILES).with_changes(attempt_history=())
    run.operations = (legacy,)
    run.fail(Op.REWRITE_DATA_FILES, 1, "boom", _now(3), failure_class=FailureClass.TIMEOUT)
    assert _attempts(run) == (
        OperationAttempt(
            attempt=1,
            size=None,
            status=OperationRunStatus.FAILED,
            started_at=_now(1),
            finished_at=_now(3),
            failure_class=FailureClass.TIMEOUT,
            error="boom",
        ),
    )


def test_replayed_outcome_leaves_the_attempt_unchanged():
    """Recording the same outcome again, even with another class, changes nothing."""
    run = _run([Op.REWRITE_DATA_FILES])
    run.start_attempt(Op.REWRITE_DATA_FILES, 1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(Op.REWRITE_DATA_FILES, 1, "oom", _now(2), failure_class=FailureClass.OOM)
    before = _attempts(run)
    run.fail(Op.REWRITE_DATA_FILES, 1, "other", _now(3), failure_class=FailureClass.OTHER)
    assert _attempts(run) == before


def test_attempt_record_is_none_for_an_unknown_attempt():
    """An attempt that has no entry reads as None."""
    run = _run()
    assert run.attempt_record(Op.REWRITE_DATA_FILES, 1) is None
