"""Tests for the TableMaintenanceRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PartitionFieldInfo,
    PartitionSpecInfo,
    SpecPartitions,
    TableId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptStatus,
    CancelledRunStatus,
    ExpireSnapshotsJobContent,
    FailedRunStatus,
    FailureClass,
    InvalidRunTransition,
    NextAttempt,
    NextStep,
    OperationAttempt,
    PendingRunStatus,
    QueuedRunStatus,
    RetryWaitingRunStatus,
    RewriteDataFilesJobContent,
    RunningRunStatus,
    RunStatusName,
    SkippedRunStatus,
    SucceededRunStatus,
    TableMaintenanceRun,
    TriggerType,
)
from tests.context.table_maintenance.fakes.job_content import job_content

RUN_1 = "mr-00000000000000000000000001"

T0 = datetime(2026, 10, 24, tzinfo=UTC)

COMPACTION = Op.REWRITE_DATA_FILES
STOPPED = "the table's maintenance stopped before this run started"


def _now(minutes: int = 0) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _run(operation: Op = Op.EXPIRE_SNAPSHOTS, **create_kwargs) -> TableMaintenanceRun:
    create_kwargs.setdefault("execution_ref", "wf-run-1")
    create_kwargs.setdefault("content", job_content(operation))
    return TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_1),
        TableId("t-1"),
        TriggerType.MANUAL,
        operation,
        _now(),
        **create_kwargs,
    )


def _with(run: TableMaintenanceRun, **changes: object) -> TableMaintenanceRun:
    """Build a run from ``run``'s fields with ``changes``, so its validators judge the result."""
    return TableMaintenanceRun.model_validate({**dict(run), **changes})


REGION = PartitionFieldInfo(
    field_id=1000, name="region", source_column="region", source_type="string", transform="identity"
)
EU = SpecPartitions(spec=PartitionSpecInfo(spec_id=0, fields=(REGION,)), values=(("eu",),))


def _attempt(n: int, status: AttemptStatus = AttemptStatus.FAILED, **fields: object) -> OperationAttempt:
    return OperationAttempt.model_validate(
        {"attempt": n, "size": ComputeSize.S, "status": status, "started_at": T0, **fields}
    )


def _retry(size: ComputeSize = ComputeSize.S) -> NextAttempt:
    return NextAttempt(step=NextStep.RETRY_SAME, size=size)


# --- one run, one operation, one status ---


def test_a_new_run_is_pending_with_no_attempt():
    """A new run of one operation is pending, with no attempt, start or finish."""
    run = _run()
    assert (run.operation, run.status, run.attempts, run.started_at, run.finished_at) == (
        Op.EXPIRE_SNAPSHOTS,
        PendingRunStatus(),
        (),
        None,
        None,
    )


def test_the_first_attempt_queues_and_starts_the_run():
    """The first submit queues the run and its attempt, which carries its job, and starts the run."""
    run = _run()
    run.start_attempt(1, "tm-es-x-a1", _now(1), size=ComputeSize.S)
    assert (run.status, run.started_at) == (QueuedRunStatus(), _now(1))
    assert (run.attempts[0].status, run.attempts[0].job_name) == (AttemptStatus.QUEUED, "tm-es-x-a1")


def test_each_attempt_keeps_its_own_job_name():
    """Every attempt keeps the name of its own job; the run started with the first."""
    run = _run()
    run.start_attempt(1, "job-a1", _now(1), size=ComputeSize.S)
    run.fail(
        1,
        "boom",
        _now(2),
        failure_class=FailureClass.OTHER,
        started_running_at=_now(1),
        event_log_finished=None,
        next_attempt=NextAttempt(step=NextStep.RETRY_SAME, size=ComputeSize.S),
    )
    run.start_attempt(2, "job-a2", _now(3), size=ComputeSize.S)
    assert [a.job_name for a in run.attempts] == ["job-a1", "job-a2"]
    assert run.started_at == _now(1)


def test_success_finishes_the_run_with_the_procedure_numbers():
    """A success finishes the run with the numbers the procedure returned."""
    run = _run()
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.succeed(1, {"deleted_data_files_count": 3}, _now(5), started_running_at=_now(2), event_log_finished=True)
    assert (run.status, run.metrics, run.finished_at, run.error) == (
        SucceededRunStatus(),
        {"deleted_data_files_count": 3},
        _now(5),
        None,
    )


def test_a_failure_with_a_retry_waits_until_the_next_attempt():
    """A run whose failed attempt will be retried waits to retry, unfinished, until the retry queues it."""
    run = _run()
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.fail(
        1,
        "boom",
        _now(2),
        failure_class=FailureClass.OTHER,
        started_running_at=None,
        event_log_finished=None,
        next_attempt=NextAttempt(step=NextStep.RETRY_SAME, size=ComputeSize.S),
    )
    assert (run.status, run.finished_at) == (RetryWaitingRunStatus(), None)
    run.start_attempt(2, None, _now(3), size=ComputeSize.S)
    assert (run.status, run.finished_at) == (QueuedRunStatus(), None)


def test_a_pending_run_is_skipped_with_its_reason():
    """A pending run is skipped with its reason in skip_reason, not in error."""
    run = _run()
    run.skip(STOPPED, _now(1))
    assert (run.status, run.skip_reason, run.error, run.finished_at) == (SkippedRunStatus(), STOPPED, None, _now(1))


def test_a_started_run_cannot_be_skipped():
    """A run whose attempt was submitted cannot be skipped."""
    run = _run()
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    with pytest.raises(InvalidRunTransition):
        run.skip(STOPPED, _now(2))


def test_a_run_keeps_what_its_job_does():
    """A run records the content every attempt of it runs with."""
    content = ExpireSnapshotsJobContent(older_than=_now(-60), retain_last=1)
    assert _run(content=content).content == content


def test_a_compaction_run_keeps_its_partitions():
    """A compaction run keeps the partitions it was created with."""
    content = RewriteDataFilesJobContent(target_file_size_bytes=1, partitions=(EU,))
    kept = _run(COMPACTION, content=content).content
    assert isinstance(kept, RewriteDataFilesJobContent)
    assert kept.partitions == (EU,)


def test_content_of_another_operation_is_refused():
    """A run holds the content of its own operation only."""
    with pytest.raises(InvalidRunTransition, match="expire_snapshots run cannot hold rewrite_data_files content"):
        _run(Op.EXPIRE_SNAPSHOTS, content=RewriteDataFilesJobContent(target_file_size_bytes=1))


def test_a_run_has_eight_status_names_and_no_partially_failed():
    """A run can wait to retry or be cancelled; with one operation per run there is no partially failed status."""
    assert {s.value for s in RunStatusName} == {
        "pending",
        "queued",
        "running",
        "retry_waiting",
        "succeeded",
        "failed",
        "skipped",
        "cancelled",
    }


# --- the run's invariants ---


def test_a_run_without_partitions_is_the_whole_table():
    """A compaction run created without partitions compacts the whole table."""
    content = _run(COMPACTION).content
    assert isinstance(content, RewriteDataFilesJobContent)
    assert content.partitions == ()


def test_a_run_built_with_content_of_another_operation_is_refused():
    """The content invariant holds for a run built directly, not only through create."""
    with pytest.raises(InvariantViolation, match="cannot hold rewrite_data_files content"):
        _with(_run(), content=RewriteDataFilesJobContent(target_file_size_bytes=1))


def test_a_run_without_attempts_is_valid():
    """A run that has not started has no attempts."""
    assert _with(_run()).attempts == ()


def test_attempts_numbered_from_one_upward_are_valid():
    """Attempts listed oldest first, numbered 1, 2, 3, make a valid run."""
    run = _with(
        _run(),
        status=RunStatusName.RUNNING,
        attempts=(_attempt(1), _attempt(2), _attempt(3, AttemptStatus.RUNNING)),
    )
    assert [a.attempt for a in run.attempts] == [1, 2, 3]


@pytest.mark.parametrize(
    "attempts",
    [
        (_attempt(1), _attempt(1, AttemptStatus.RUNNING)),
        (_attempt(1), _attempt(3), _attempt(2, AttemptStatus.RUNNING)),
    ],
)
def test_attempt_numbers_must_increase(attempts):
    """An attempt listed twice, or out of order, is refused."""
    with pytest.raises(InvariantViolation, match="increase"):
        _with(_run(), status=RunStatusName.RUNNING, attempts=attempts)


def test_attempts_must_start_at_one():
    """A run whose first attempt is not attempt 1 is refused: there is no history from before attempts."""
    with pytest.raises(InvariantViolation, match="start at 1"):
        _with(_run(), status=RunStatusName.RUNNING, attempts=(_attempt(2, AttemptStatus.RUNNING),))


@pytest.mark.parametrize(
    ("status", "skip_reason", "attempts"),
    [(RunStatusName.SKIPPED, None, ()), (RunStatusName.FAILED, STOPPED, (_attempt(1),))],
)
def test_a_skip_reason_goes_exactly_with_a_skipped_run(status, skip_reason, attempts):
    """A skipped run needs its reason, and no other run may carry one."""
    with pytest.raises(InvariantViolation, match="skip reason"):
        _with(_run(), status=status, skip_reason=skip_reason, finished_at=_now(1), attempts=attempts)


@pytest.mark.parametrize(
    ("status", "finished_at", "attempts"),
    [
        (RunStatusName.SUCCEEDED, None, (_attempt(1, AttemptStatus.SUCCEEDED),)),
        (RunStatusName.FAILED, None, (_attempt(1),)),
        (RunStatusName.PENDING, _now(1), ()),
        (RunStatusName.QUEUED, _now(1), (_attempt(1, AttemptStatus.QUEUED),)),
        (RunStatusName.RUNNING, _now(1), (_attempt(1, AttemptStatus.RUNNING),)),
    ],
)
def test_a_finish_time_goes_exactly_with_a_terminal_status(status, finished_at, attempts):
    """A succeeded, failed, skipped or cancelled run has a finish time; a pending, queued or running one has none."""
    with pytest.raises(InvariantViolation, match="finish time"):
        _with(_run(), status=status, finished_at=finished_at, attempts=attempts)


@pytest.mark.parametrize(
    ("status", "finished_at", "attempts"),
    [
        (RunStatusName.QUEUED, None, ()),
        (RunStatusName.RUNNING, None, ()),
        (RunStatusName.FAILED, _now(1), ()),
        (RunStatusName.SUCCEEDED, _now(1), ()),
        (RunStatusName.RUNNING, None, (_attempt(1, AttemptStatus.QUEUED),)),
        (RunStatusName.QUEUED, None, (_attempt(1), _attempt(2, AttemptStatus.RUNNING))),
        (RunStatusName.FAILED, _now(1), (_attempt(1, AttemptStatus.SUCCEEDED),)),
        (RunStatusName.PENDING, None, (_attempt(1, AttemptStatus.QUEUED),)),
    ],
)
def test_the_status_is_the_latest_attempts_or_pending_skipped_or_cancelled_without_one(status, finished_at, attempts):
    """A run with attempts reads its latest attempt's status; a run without one is pending, skipped or cancelled."""
    with pytest.raises(InvariantViolation, match="latest attempt's status|has no attempt"):
        _with(_run(), status=status, finished_at=finished_at, attempts=attempts)


def test_a_skipped_run_without_attempts_is_valid():
    """A run skipped before it started has no attempt, and that is consistent."""
    run = _with(_run(), status=RunStatusName.SKIPPED, skip_reason=STOPPED, finished_at=_now(1))
    assert (run.status, run.attempts) == (SkippedRunStatus(), ())


def test_a_run_needs_an_operation():
    """A run is created for one maintenance operation, not for a name."""
    with pytest.raises(InvariantViolation):
        _run("expire_snapshots")  # ty: ignore[invalid-argument-type]


# --- create ---


def test_create_records_the_priority_it_is_given():
    """A run keeps the priority it was started with."""
    assert _run(priority=TablePriority.P1).priority is TablePriority.P1


def test_create_without_a_priority_records_p3():
    """A run started without a priority records the default, P3."""
    assert _run().priority is TablePriority.P3


def test_create_records_its_operation_and_starts_pending():
    """Creating a run records its operation and creation time, pending, with nothing measured yet."""
    run = _run(COMPACTION)
    assert (run.operation, run.status, run.created_at, run.finished_at) == (
        COMPACTION,
        PendingRunStatus(),
        _now(),
        None,
    )
    assert (run.content, run.metrics, run.error, run.skip_reason) == (job_content(COMPACTION), {}, None, None)


def test_create_records_the_workflow_id():
    """A new run records the execution reference of its workflow."""
    assert _run().execution_ref == "wf-run-1"


def test_create_rejects_an_empty_execution_ref():
    """A run without an execution reference is rejected."""
    with pytest.raises(ValueError, match="execution reference"):
        _run(execution_ref="")


# --- status ---


def test_the_run_status_follows_its_attempt():
    """The run goes pending, queued, running, then succeeded and finished."""
    run = _run(COMPACTION)
    assert run.status == PendingRunStatus()
    run.start_attempt(1, "app-1", _now(1), size=ComputeSize.S)
    assert run.status == QueuedRunStatus()
    run.record_attempt_running(1, _now(1), _now(1))
    assert run.status == RunningRunStatus()
    assert run.finished_at is None
    run.succeed(1, {"files": 3}, _now(2))
    assert run.status == SucceededRunStatus()
    assert run.finished_at == _now(2)


def test_a_failed_attempt_fails_and_finishes_the_run():
    """A failure with nothing after it leaves the run failed, finished, with the attempt's error."""
    run = _run(COMPACTION)
    run.start_attempt(1, "a", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(4))
    assert (run.status, run.finished_at, run.error) == (FailedRunStatus(), _now(4), "boom")


def test_the_run_reads_the_status_of_its_latest_attempt():
    """After a failed attempt, the retry queues the run again, then runs it."""
    run = _run(COMPACTION)
    run.start_attempt(1, "a1", _now(1), size=ComputeSize.S)
    run.record_attempt_running(1, _now(2), _now(2))
    run.fail(1, "boom", _now(3), next_attempt=_retry())
    run.start_attempt(2, "a2", _now(4), size=ComputeSize.S)
    assert run.status == QueuedRunStatus()
    run.record_attempt_running(2, _now(5), _now(5))
    assert run.status == RunningRunStatus()
    assert [a.status for a in run.attempts] == [AttemptStatus.FAILED, AttemptStatus.RUNNING]


# --- skip ---


def test_a_skipped_run_cannot_be_started():
    """A skipped run never gets an attempt."""
    run = _run()
    run.skip(STOPPED, _now(1))
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(1, "a", _now(2), size=ComputeSize.S)
    assert run.attempts == ()


def test_skip_only_from_pending():
    """A finished or already skipped run cannot be skipped."""
    run = _run()
    run.start_attempt(1, "a", _now(1), size=ComputeSize.S)
    run.succeed(1, {}, _now(2))
    with pytest.raises(InvalidRunTransition):
        run.skip(STOPPED, _now(3))
    skipped = _run()
    skipped.skip(STOPPED, _now(1))
    with pytest.raises(InvalidRunTransition):
        skipped.skip("again", _now(2))
    assert skipped.skip_reason == STOPPED


# --- attempts ---


def test_stale_attempt_result_ignored():
    """A result for an earlier attempt does not change the current attempt."""
    run = _run()
    run.start_attempt(1, "a1", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), next_attempt=_retry())
    run.start_attempt(2, "a2", _now(3), size=ComputeSize.S)
    run.succeed(1, {"x": 1}, _now(4))
    run.fail(1, "late", _now(4))
    assert run.status == QueuedRunStatus()
    assert len(run.attempts) == 2
    assert run.attempts[-1].job_name == "a2"


def test_retry_clears_previous_outcome():
    """Starting a new attempt clears the run's error and metrics, and it has no finish time; it keeps its start."""
    run = _run(COMPACTION)
    run.start_attempt(1, "a1", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), next_attempt=_retry())
    assert run.error == "boom"
    run.start_attempt(2, "a2", _now(3), size=ComputeSize.S)
    assert run.error is None and run.finished_at is None and run.metrics == {}
    assert run.started_at == _now(1)
    assert run.attempts[1].started_at == _now(3)
    assert run.status == QueuedRunStatus()


def test_start_attempt_idempotent_and_guarded():
    """Starting the same attempt twice changes nothing and invalid attempt numbers are rejected."""
    run = _run()
    run.start_attempt(1, "a1", _now(1), size=ComputeSize.S)
    run.start_attempt(1, "a1", _now(2), size=ComputeSize.S)
    assert run.started_at == _now(1)
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(1, "other", _now(2), size=ComputeSize.S)
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(3, "a3", _now(2), size=ComputeSize.S)
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(2, "a2", _now(2), size=ComputeSize.S)
    run.succeed(1, {}, _now(3))
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(2, "a2", _now(4), size=ComputeSize.S)


def test_duplicate_result_is_idempotent():
    """Recording the same success twice keeps the first result."""
    run = _run()
    run.start_attempt(1, "a", _now(1), size=ComputeSize.S)
    metrics = {"files": 2}
    run.succeed(1, metrics, _now(2))
    metrics["files"] = 99
    run.succeed(1, {"files": 5}, _now(3))
    assert run.status == SucceededRunStatus()
    assert run.metrics == {"files": 2}
    assert run.finished_at == _now(2)
    with pytest.raises(InvalidRunTransition):
        run.fail(1, "boom", _now(4))


def test_duplicate_fail_idempotent_and_succeed_after_fail_raises():
    """Recording the same failure twice keeps it, but a success after a failure is rejected."""
    run = _run()
    run.start_attempt(1, "a", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2))
    run.fail(1, "boom2", _now(3))
    assert run.error == "boom"
    with pytest.raises(InvalidRunTransition):
        run.succeed(1, {}, _now(4))


def test_result_for_future_or_unstarted_attempt_raises():
    """A result for a future or not yet started attempt is rejected."""
    run = _run()
    with pytest.raises(InvalidRunTransition):
        run.succeed(1, {}, _now(1))
    run.start_attempt(1, "a", _now(1), size=ComputeSize.S)
    with pytest.raises(InvalidRunTransition):
        run.fail(2, "x", _now(2))


def test_start_attempt_without_a_job_name_then_attach_it():
    """An attempt can start without a job name and get it attached afterwards."""
    run = _run(COMPACTION)
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    assert run.attempts[0].job_name is None
    run.start_attempt(1, None, _now(2), size=ComputeSize.S)
    run.attach_job_name(1, "j1")
    run.attach_job_name(1, "j1")
    run.start_attempt(1, None, _now(3), size=ComputeSize.S)
    assert (len(run.attempts), run.attempts[0].job_name, run.started_at) == (1, "j1", _now(1))


def test_attach_job_name_is_guarded():
    """Attaching a job name is rejected for an unstarted, other or finished attempt, or a second name."""
    run = _run(COMPACTION)
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(1, "j1")
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.attach_job_name(1, "j1")
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(1, "other")
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(2, "j2")
    run.succeed(1, {}, _now(2))
    with pytest.raises(InvalidRunTransition):
        run.attach_job_name(1, "j1")


def test_attaching_a_job_name_names_only_the_current_attempt():
    """The job name attached to attempt 2 leaves attempt 1's name alone."""
    run = _run(COMPACTION)
    run.start_attempt(1, "j1", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), next_attempt=_retry())
    run.start_attempt(2, None, _now(3), size=ComputeSize.S)
    run.attach_job_name(2, "j2")
    assert [a.job_name for a in run.attempts] == ["j1", "j2"]


def test_forbidden_transition_still_raises_invalid_run_transition():
    """A forbidden transition raises InvalidRunTransition, not an InvariantViolation."""
    run = _run()
    with pytest.raises(InvalidRunTransition):
        run.succeed(1, {}, _now(1))
    assert issubclass(InvalidRunTransition, ValueError)


def test_an_attempt_update_revalidates():
    """Changing an attempt goes through validation and rejects a wrong type."""
    with pytest.raises(InvariantViolation):
        _attempt(1).with_changes(attempt="many")


def test_an_attempt_is_immutable():
    """An attempt cannot be changed in place."""
    attempt = _attempt(1)
    with pytest.raises(AttributeError, match="is immutable"):
        attempt.attempt = 3


def test_run_rejects_a_wrong_typed_assignment():
    """Assigning a wrong type to a run field raises InvariantViolation."""
    run = _run()
    with pytest.raises(InvariantViolation):
        run.created_at = "yesterday"  # ty: ignore[invalid-assignment]


def test_failed_state_change_leaves_the_run_unchanged():
    """A rejected transition leaves the run as it was."""
    run = _run()
    before = run.model_dump()
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(5, None, _now(1), size=ComputeSize.S)
    assert run.model_dump() == before


def test_start_attempt_appends_a_queued_attempt_with_its_size():
    """Starting an attempt records it as queued at its size, with its job."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.M)
    assert run.attempts == (
        OperationAttempt(
            attempt=1, size=ComputeSize.M, status=AttemptStatus.QUEUED, started_at=_now(1), job_name="job-1"
        ),
    )


def test_restarting_the_running_attempt_adds_no_entry():
    """Starting the running attempt again leaves its one entry."""
    run = _run(COMPACTION)
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.start_attempt(1, "job-1", _now(2), size=ComputeSize.S)
    assert len(run.attempts) == 1
    assert run.attempts[0].started_at == _now(1)


def test_fail_records_class_error_event_log_and_next_step_on_the_attempt():
    """A failure records its class, raw error, event log state and next step on its attempt."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(
        1,
        "java.lang.OutOfMemoryError: Java heap space",
        _now(5),
        failure_class=FailureClass.OOM,
        event_log_finished=False,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    assert run.attempt_record(1) == OperationAttempt(
        attempt=1,
        size=ComputeSize.S,
        status=AttemptStatus.FAILED,
        started_at=_now(1),
        job_name="job-1",
        finished_at=_now(5),
        failure_class=FailureClass.OOM,
        error="java.lang.OutOfMemoryError: Java heap space",
        event_log_finished=False,
        next_step=NextStep.RETRY_LARGER,
        next_size=ComputeSize.M,
    )
    assert run.error == "java.lang.OutOfMemoryError: Java heap space"


def test_fail_without_a_class_records_other():
    """A failure recorded without a class is other, with no next step."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2))
    record = run.attempt_record(1)
    assert record is not None
    assert record.failure_class is FailureClass.OTHER
    assert record.next_step is None


def test_succeed_marks_the_attempt_done():
    """A success marks its attempt succeeded with next step done."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.M)
    run.succeed(1, {"rewritten_data_files_count": 3}, _now(4), event_log_finished=True)
    record = run.attempt_record(1)
    assert record is not None
    assert record.status is AttemptStatus.SUCCEEDED
    assert record.finished_at == _now(4)
    assert record.event_log_finished is True
    assert record.next_step is NextStep.DONE
    assert record.next_size is None
    assert record.failure_class is None


def test_three_attempts_keep_three_entries():
    """S fails, M fails, L succeeds: three entries, oldest first."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(
        1,
        "oom",
        _now(2),
        failure_class=FailureClass.OOM,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    run.start_attempt(2, "job-2", _now(3), size=ComputeSize.M)
    run.fail(
        2,
        "oom",
        _now(4),
        failure_class=FailureClass.OOM,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.L),
    )
    run.start_attempt(3, "job-3", _now(5), size=ComputeSize.L)
    run.succeed(3, {}, _now(6))
    assert [(a.attempt, a.size, a.status, a.next_step, a.next_size) for a in run.attempts] == [
        (1, ComputeSize.S, AttemptStatus.FAILED, NextStep.RETRY_LARGER, ComputeSize.M),
        (2, ComputeSize.M, AttemptStatus.FAILED, NextStep.RETRY_LARGER, ComputeSize.L),
        (3, ComputeSize.L, AttemptStatus.SUCCEEDED, NextStep.DONE, None),
    ]
    assert run.error is None


def test_replayed_outcome_leaves_the_attempt_unchanged():
    """Recording the same outcome again, even with another class, changes nothing."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(1, "oom", _now(2), failure_class=FailureClass.OOM)
    before = run.attempts
    run.fail(1, "other", _now(3), failure_class=FailureClass.OTHER)
    assert run.attempts == before


def test_attempt_record_is_none_for_an_unknown_attempt():
    """An attempt that has no entry reads as None."""
    assert _run().attempt_record(1) is None


def test_an_attempt_cannot_start_running_before_it_was_submitted():
    """A running time earlier than the submit time is rejected."""
    with pytest.raises(InvariantViolation):
        _attempt(1, AttemptStatus.RUNNING, started_running_at=T0 - timedelta(seconds=1))


def test_a_queued_or_running_attempt_is_not_finished():
    """Only an attempt with an outcome is finished."""
    assert not _attempt(1, AttemptStatus.QUEUED).finished
    assert not _attempt(1, AttemptStatus.RUNNING).finished
    assert _attempt(1, AttemptStatus.FAILED).finished
    assert _attempt(1, AttemptStatus.SUCCEEDED).finished


# --- the driver running ---


def _queued_run() -> TableMaintenanceRun:
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    return run


def test_a_submitted_attempt_is_queued():
    """A submitted attempt and its run wait in the queue until the job runs."""
    run = _queued_run()
    assert run.status == QueuedRunStatus()
    assert run.attempts[0].status is AttemptStatus.QUEUED
    assert run.attempts[0].started_running_at is None
    assert not run.attempts[0].finished


def test_restarting_a_queued_attempt_is_a_no_op_that_attaches_the_job_name():
    """Starting the queued attempt again changes nothing but a missing job name."""
    run = _run(COMPACTION)
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.start_attempt(1, "job-1", _now(2), size=ComputeSize.S)
    assert run.attempts[0].job_name == "job-1"
    assert len(run.attempts) == 1


def test_record_running_moves_queued_to_running():
    """Recording that the driver runs moves the attempt and the run to running."""
    run = _queued_run()
    run.record_attempt_running(1, _now(3), _now(4))
    assert run.status == RunningRunStatus()
    assert run.attempts[0].status is AttemptStatus.RUNNING
    assert run.attempts[0].started_running_at == _now(3)


def test_record_running_twice_is_a_no_op():
    """A second report that the driver runs keeps the first running time."""
    run = _queued_run()
    run.record_attempt_running(1, _now(3), _now(4))
    run.record_attempt_running(1, _now(5), _now(6))
    assert run.attempts[0].started_running_at == _now(3)


def test_running_before_the_submit_is_clamped():
    """A running time before the submit is raised to the submit time."""
    run = _queued_run()
    run.record_attempt_running(1, _now(1) - timedelta(seconds=5), _now(4))
    assert run.attempts[0].started_running_at == _now(1)


def test_running_after_now_is_clamped():
    """A running time in the future is lowered to now."""
    run = _queued_run()
    run.record_attempt_running(1, _now(4) + timedelta(seconds=5), _now(4))
    assert run.attempts[0].started_running_at == _now(4)


def test_a_result_fills_a_missing_running_time():
    """A result carrying the running time records it on an attempt that never got one."""
    run = _queued_run()
    run.succeed(1, {}, _now(5), started_running_at=_now(3))
    assert run.status == SucceededRunStatus()
    assert run.attempts[0].started_running_at == _now(3)


def test_a_result_keeps_the_running_time_already_recorded():
    """A result does not replace a running time the attempt already has."""
    run = _queued_run()
    run.record_attempt_running(1, _now(2), _now(3))
    run.fail(1, "boom", _now(5), started_running_at=_now(4))
    assert run.attempts[0].started_running_at == _now(2)


def test_record_running_on_a_finished_attempt_only_fills_the_time():
    """A running time that arrives after the result is recorded within the attempt, status unchanged."""
    run = _queued_run()
    run.fail(1, "boom", _now(5))
    run.record_attempt_running(1, _now(9), _now(10))
    assert run.status == FailedRunStatus()
    assert run.attempts[0].status is AttemptStatus.FAILED
    assert run.attempts[0].started_running_at == _now(5)
    run.record_attempt_running(1, _now(2), _now(10))
    assert run.attempts[0].started_running_at == _now(5)


def test_record_running_of_a_lower_attempt_is_a_no_op():
    """A running report for an earlier attempt changes nothing."""
    run = _queued_run()
    run.fail(1, "boom", _now(2), next_attempt=_retry())
    run.start_attempt(2, "job-2", _now(3), size=ComputeSize.S)
    run.record_attempt_running(1, _now(4), _now(5))
    assert run.status == QueuedRunStatus()
    assert [a.started_running_at for a in run.attempts] == [None, None]


def test_record_running_of_an_unstarted_attempt_is_refused():
    """A running report for an attempt that was never started is rejected."""
    run = _run(COMPACTION)
    with pytest.raises(InvalidRunTransition):
        run.record_attempt_running(1, _now(1), _now(2))
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    with pytest.raises(InvalidRunTransition):
        run.record_attempt_running(2, _now(1), _now(2))


def test_queued_attempt_can_fail_without_running():
    """An attempt can fail while still queued, with no running time."""
    run = _queued_run()
    run.fail(1, "queue wait limit", _now(5))
    assert run.status == FailedRunStatus()
    assert run.attempts[0].started_running_at is None


def test_attach_job_name_accepts_a_queued_or_running_attempt():
    """The job name can be attached while the attempt is queued and while it runs."""
    run = _run(COMPACTION)
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.attach_job_name(1, "j1")
    run.record_attempt_running(1, _now(2), _now(3))
    run.attach_job_name(1, "j1")
    assert run.attempts[0].job_name == "j1"


def test_a_result_earlier_than_the_submit_still_records_a_running_time_within_the_attempt():
    """A result stamped before the submit (clock skew) is accepted; the running time is the submit time."""
    run = _queued_run()
    run.succeed(1, {}, _now(1) - timedelta(seconds=5), started_running_at=_now(3))
    assert run.status == SucceededRunStatus()
    assert run.attempts[0].started_running_at == _now(1)


def test_a_running_time_reported_after_a_skewed_finish_stays_within_the_attempt():
    """A running time that arrives after a finish stamped before the submit is the submit time."""
    run = _queued_run()
    run.fail(1, "boom", _now(1) - timedelta(seconds=5))
    run.record_attempt_running(1, _now(3), _now(4))
    assert run.attempts[0].started_running_at == _now(1)


def test_a_result_clamps_a_running_time_before_the_submit():
    """The running time a result carries is raised to the submit time when it is earlier."""
    run = _queued_run()
    run.fail(1, "boom", _now(5), started_running_at=_now(1) - timedelta(seconds=5))
    assert run.attempts[0].started_running_at == _now(1)


def test_a_result_clamps_a_running_time_after_the_finish():
    """The running time a result carries is lowered to the finish time when it is later."""
    run = _queued_run()
    run.succeed(1, {}, _now(5), started_running_at=_now(9))
    assert run.attempts[0].started_running_at == _now(5)


# --- priority ---


def test_raise_only_upward():
    """A run's priority is raised only by a priority that outranks it."""
    run = _run(priority=TablePriority.P2)

    assert run.raise_priority(TablePriority.P3) is False
    assert run.raise_priority(TablePriority.P2) is False
    assert run.priority is TablePriority.P2
    assert run.raise_priority(TablePriority.P0) is True
    assert run.priority is TablePriority.P0


def test_finished_run_is_not_raised():
    """A succeeded run keeps its priority."""
    run = _run()
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.succeed(1, {}, _now(2))
    assert run.finished_at is not None

    assert run.raise_priority(TablePriority.P0) is False
    assert run.priority is TablePriority.P3


def test_a_skipped_run_is_not_raised():
    """A skipped run never runs, so it keeps its priority."""
    run = _run()
    run.skip(STOPPED, _now(1))
    assert run.raise_priority(TablePriority.P0) is False
    assert run.priority is TablePriority.P3


@pytest.mark.parametrize("retried_first", [False, True])
@pytest.mark.parametrize(
    "next_attempt",
    [None, NextAttempt(step=NextStep.ATTEMPTS_USED), NextAttempt(step=NextStep.NEEDS_ATTENTION)],
)
def test_a_failed_run_that_will_not_retry_is_not_raised(next_attempt, retried_first):
    """A failure with no retry after it ends the run, so it keeps its priority, even after an earlier retry."""
    run = _run()
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    if retried_first:
        run.fail(1, "boom", _now(2), next_attempt=_retry())
        run.start_attempt(2, "job-2", _now(3), size=ComputeSize.S)
    run.fail(run.attempts[-1].attempt, "boom", _now(4), next_attempt=next_attempt)
    assert run.raise_priority(TablePriority.P0) is False
    assert run.priority is TablePriority.P3


@pytest.mark.parametrize("step", [NextStep.RETRY_SAME, NextStep.RETRY_LARGER])
def test_a_run_waiting_for_its_retry_is_raised(step):
    """During the backoff before a retry the run waits to retry, with no finish time, and a raise lands."""
    run = _run()
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), next_attempt=NextAttempt(step=step, size=ComputeSize.M))
    assert (run.status, run.finished_at) == (RetryWaitingRunStatus(), None)

    assert run.raise_priority(TablePriority.P0) is True
    assert run.priority is TablePriority.P0


@pytest.mark.parametrize("running", [False, True])
def test_a_queued_or_running_run_is_raised(running):
    """A run whose attempt waits in the queue or runs takes the raise."""
    run = _run()
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    if running:
        run.record_attempt_running(1, _now(2), _now(2))
    assert run.status == (RunningRunStatus() if running else QueuedRunStatus())
    assert run.raise_priority(TablePriority.P0) is True
    assert run.priority is TablePriority.P0


def test_a_pending_run_is_raised():
    """A run not started yet takes the raise, so its first attempt submits at the new priority."""
    run = _run()
    assert run.raise_priority(TablePriority.P1) is True
    assert run.priority is TablePriority.P1


def test_the_current_attempt_is_the_latest_attempts_number():
    """A run reads 0 before its first submit, then the number of its latest attempt."""
    run = _run()
    assert run.current_attempt == 0
    run.start_attempt(1, None, _now(1), size=ComputeSize.S)
    run.fail(1, "boom", _now(2), next_attempt=_retry())
    run.start_attempt(2, None, _now(3), size=ComputeSize.S)
    assert run.current_attempt == 2


def test_an_attempt_needs_a_size():
    """An attempt always runs at a size; one without is refused."""
    with pytest.raises(InvariantViolation, match="size"):
        OperationAttempt(attempt=1, size=None, status=AttemptStatus.QUEUED, started_at=_now())  # ty: ignore[invalid-argument-type]


# --- waiting to retry and cancelling ---

CANCELLED_BY_WORKFLOW = "the maintenance workflow was cancelled"


def _running_run() -> TableMaintenanceRun:
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    run.record_attempt_running(1, _now(2), _now(2))
    return run


def _waiting_run() -> TableMaintenanceRun:
    run = _running_run()
    run.fail(1, "boom", _now(3), next_attempt=_retry())
    return run


def _cancelled_run() -> TableMaintenanceRun:
    run = _running_run()
    run.cancel_attempt(1, CANCELLED_BY_WORKFLOW, _now(3))
    return run


def _succeeded_run() -> TableMaintenanceRun:
    run = _running_run()
    run.succeed(1, {}, _now(3))
    return run


def _failed_run() -> TableMaintenanceRun:
    run = _running_run()
    run.fail(1, "boom", _now(3))
    return run


def _skipped_run() -> TableMaintenanceRun:
    run = _run(COMPACTION)
    run.skip(STOPPED, _now(1))
    return run


def test_a_failure_that_retries_leaves_the_run_waiting_with_no_finish_time():
    """A failed attempt with a retry to follow leaves the run waiting, unfinished, with the attempt's error."""
    run = _running_run()
    run.fail(1, "boom", _now(3), next_attempt=NextAttempt(step=NextStep.RETRY_SAME, size=ComputeSize.S))
    assert run.status == RetryWaitingRunStatus()
    assert (run.finished_at, run.error) == (None, "boom")
    assert (run.attempts[-1].status, run.attempts[-1].finished_at) == (AttemptStatus.FAILED, _now(3))


@pytest.mark.parametrize(
    "next_attempt",
    [
        None,
        NextAttempt(step=NextStep.ATTEMPTS_USED),
        NextAttempt(step=NextStep.NOT_RETRIED),
        NextAttempt(step=NextStep.NEEDS_ATTENTION),
        NextAttempt(step=NextStep.STILL_RUNNING),
    ],
)
def test_a_failure_that_does_not_retry_fails_the_run(next_attempt):
    """A failed attempt with no retry to follow fails and finishes the run."""
    run = _running_run()
    run.fail(1, "boom", _now(3), next_attempt=next_attempt)
    assert (run.status, run.finished_at) == (FailedRunStatus(), _now(3))


def test_a_waiting_run_starts_its_next_attempt_queued():
    """The retry of a waiting run queues it again and clears the failed attempt's outcome from the run."""
    run = _waiting_run()
    run.start_attempt(2, "job-2", _now(4), size=ComputeSize.M)
    assert (run.status, run.finished_at, run.error) == (QueuedRunStatus(), None, None)
    assert [a.status for a in run.attempts] == [AttemptStatus.FAILED, AttemptStatus.QUEUED]


def test_a_failed_run_cannot_start_another_attempt():
    """A run that failed with no retry to follow has ended: no attempt follows it."""
    run = _failed_run()
    with pytest.raises(InvalidRunTransition):
        run.start_attempt(2, "job-2", _now(4), size=ComputeSize.S)
    assert len(run.attempts) == 1


def test_a_replayed_failure_of_a_waiting_run_changes_nothing():
    """Recording the waiting run's failure again keeps the run waiting with the first failure."""
    run = _waiting_run()
    before = run.model_dump()
    run.fail(1, "again", _now(5))
    assert run.model_dump() == before


def test_a_waiting_run_refuses_a_success_of_its_failed_attempt():
    """The failed attempt of a waiting run cannot succeed afterwards."""
    run = _waiting_run()
    with pytest.raises(InvalidRunTransition):
        run.succeed(1, {}, _now(5))
    assert run.status == RetryWaitingRunStatus()


@pytest.mark.parametrize("running", [False, True])
def test_cancelling_the_attempt_in_flight_cancels_the_run(running):
    """A cancel of the queued or running attempt fails it as cancelled and cancels and finishes the run."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    if running:
        run.record_attempt_running(1, _now(2), _now(2))
    run.cancel_attempt(1, CANCELLED_BY_WORKFLOW, _now(3), started_running_at=_now(2), event_log_finished=False)
    assert (run.status, run.finished_at, run.error, run.metrics) == (
        CancelledRunStatus(),
        _now(3),
        CANCELLED_BY_WORKFLOW,
        {},
    )
    assert run.attempts[-1] == OperationAttempt(
        attempt=1,
        size=ComputeSize.S,
        status=AttemptStatus.FAILED,
        started_at=_now(1),
        job_name="job-1",
        started_running_at=_now(2),
        finished_at=_now(3),
        failure_class=FailureClass.CANCELLED,
        error=CANCELLED_BY_WORKFLOW,
        event_log_finished=False,
        next_step=NextStep.CANCELLED,
    )


def test_cancelling_an_earlier_or_recorded_attempt_changes_nothing():
    """A cancel of an earlier attempt, or of one already recorded, leaves the run as it is."""
    retried = _waiting_run()
    retried.start_attempt(2, "job-2", _now(4), size=ComputeSize.S)
    before = retried.model_dump()
    retried.cancel_attempt(1, CANCELLED_BY_WORKFLOW, _now(5))
    assert retried.model_dump() == before
    cancelled = _cancelled_run()
    before = cancelled.model_dump()
    cancelled.cancel_attempt(1, "again", _now(5))
    assert cancelled.model_dump() == before


def test_cancel_attempt_refuses_a_finished_attempt_and_an_unstarted_one():
    """A succeeded attempt cannot be cancelled, nor one that was never started."""
    run = _succeeded_run()
    with pytest.raises(InvalidRunTransition):
        run.cancel_attempt(1, CANCELLED_BY_WORKFLOW, _now(5))
    assert run.status == SucceededRunStatus()
    with pytest.raises(InvalidRunTransition):
        _run().cancel_attempt(1, CANCELLED_BY_WORKFLOW, _now(5))


@pytest.mark.parametrize("make", [_waiting_run, _run], ids=["retry_waiting", "pending"])
def test_a_waiting_run_is_cancelled_without_an_attempt(make):
    """A run with no attempt in flight, waiting to retry or not started, is cancelled and finished."""
    run = make()
    attempts = run.attempts
    run.cancel(_now(5))
    assert (run.status, run.finished_at, run.attempts) == (CancelledRunStatus(), _now(5), attempts)


@pytest.mark.parametrize("running", [False, True])
def test_cancel_refuses_a_run_in_flight(running):
    """A run whose attempt is in flight is cancelled through that attempt, not as a whole."""
    run = _run(COMPACTION)
    run.start_attempt(1, "job-1", _now(1), size=ComputeSize.S)
    if running:
        run.record_attempt_running(1, _now(2), _now(2))
    before = run.model_dump()
    with pytest.raises(InvalidRunTransition, match="cancel_attempt"):
        run.cancel(_now(3))
    assert run.model_dump() == before


@pytest.mark.parametrize("make", [_succeeded_run, _failed_run, _skipped_run, _cancelled_run])
def test_cancel_refuses_a_finished_run(make):
    """A run that has ended cannot be cancelled."""
    run = make()
    before = run.model_dump()
    with pytest.raises(InvalidRunTransition):
        run.cancel(_now(5))
    assert run.model_dump() == before


def test_a_cancelled_run_is_not_raised():
    """A cancelled run has ended, so it keeps its priority."""
    run = _cancelled_run()
    assert run.raise_priority(TablePriority.P0) is False
    assert run.priority is TablePriority.P3


def test_a_cancelled_run_without_attempts_is_valid():
    """A run cancelled before it started has no attempt, and that is consistent."""
    run = _with(_run(), status=RunStatusName.CANCELLED, finished_at=_now(1))
    assert (run.status, run.attempts) == (CancelledRunStatus(), ())


def _retrying(n: int) -> OperationAttempt:
    """Return attempt ``n``, failed, with a retry at the same size to follow."""
    return _attempt(n, next_step=NextStep.RETRY_SAME, next_size=ComputeSize.S)


@pytest.mark.parametrize(
    ("status", "finished_at", "attempts"),
    [
        (RunStatusName.RETRY_WAITING, None, (_retrying(1),)),
        (RunStatusName.CANCELLED, _now(1), (_attempt(1, next_step=NextStep.CANCELLED),)),
        (RunStatusName.CANCELLED, _now(1), (_retrying(1),)),
        (RunStatusName.FAILED, _now(1), (_retrying(1),)),
        (RunStatusName.FAILED, _now(1), (_attempt(1, next_step=NextStep.CANCELLED),)),
    ],
    ids=[
        "waiting",
        "cancelled",
        "cancelled-while-waiting",
        "an-old-failed-run-with-a-retry",
        "an-old-failed-run-that-was-cancelled",
    ],
)
def test_a_failed_latest_attempt_reads_its_run_status(status, finished_at, attempts):
    """A failed latest attempt reads waiting when it retries, cancelled when cancelled; a run stored failed loads."""
    run = _with(_run(), status=status, finished_at=finished_at, attempts=attempts)
    assert run.status.name is status


@pytest.mark.parametrize(
    ("status", "finished_at", "attempts"),
    [
        (RunStatusName.RETRY_WAITING, None, ()),
        (RunStatusName.RETRY_WAITING, None, (_attempt(1),)),
        (RunStatusName.RETRY_WAITING, None, (_attempt(1, next_step=NextStep.NOT_RETRIED),)),
        (RunStatusName.RETRY_WAITING, None, (_attempt(1, AttemptStatus.QUEUED),)),
        (RunStatusName.CANCELLED, _now(1), (_attempt(1),)),
        (RunStatusName.CANCELLED, _now(1), (_attempt(1, AttemptStatus.RUNNING),)),
        (RunStatusName.SUCCEEDED, _now(1), (_retrying(1),)),
    ],
)
def test_waiting_and_cancelled_must_agree_with_the_latest_attempt(status, finished_at, attempts):
    """A waiting run's latest attempt failed and retries; a cancelled run's was cancelled or retries, or it has none."""
    with pytest.raises(InvariantViolation, match="latest attempt's status|has no attempt"):
        _with(_run(), status=status, finished_at=finished_at, attempts=attempts)


@pytest.mark.parametrize(
    ("status", "finished_at", "attempts"),
    [
        (RunStatusName.RETRY_WAITING, _now(1), (_retrying(1),)),
        (RunStatusName.CANCELLED, None, (_attempt(1, next_step=NextStep.CANCELLED),)),
        (RunStatusName.CANCELLED, None, ()),
    ],
)
def test_a_waiting_run_has_no_finish_time_and_a_cancelled_one_has_one(status, finished_at, attempts):
    """Waiting to retry has not ended, so it has no finish time; a cancelled run has ended and has one."""
    with pytest.raises(InvariantViolation, match="finish time"):
        _with(_run(), status=status, finished_at=finished_at, attempts=attempts)
