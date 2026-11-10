"""Tests for the TableMaintenanceRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from base.model import validated_copy
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    InvalidRunTransition,
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
    """A forbidden transition raises InvalidRunTransition, not a ValidationError."""
    run = _run([Op.EXPIRE_SNAPSHOTS])
    with pytest.raises(InvalidRunTransition):
        run.succeed(Op.EXPIRE_SNAPSHOTS, 1, {}, _now(1))
    assert issubclass(InvalidRunTransition, ValueError)


def test_operation_update_revalidates():
    """Changing an operation goes through validation and rejects a wrong type."""
    operation = OperationRun(operation=Op.EXPIRE_SNAPSHOTS)
    with pytest.raises(ValidationError):
        validated_copy(operation, attempts="many")


def test_operation_run_is_immutable():
    """An operation run cannot be changed in place."""
    operation = OperationRun(operation=Op.EXPIRE_SNAPSHOTS)
    with pytest.raises(ValidationError):
        operation.attempts = 3


def test_run_rejects_a_wrong_typed_assignment():
    """Assigning a wrong type to a run field raises ValidationError."""
    run = _run()
    with pytest.raises(ValidationError):
        run.created_at = "yesterday"  # ty: ignore[invalid-assignment]


def test_failed_state_change_leaves_the_run_unchanged():
    """A rejected transition leaves the operations as they were."""
    run = _run([Op.EXPIRE_SNAPSHOTS])
    before = run.model_dump()
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(Op.EXPIRE_SNAPSHOTS, 5, None, _now(1))
    assert run.model_dump() == before
