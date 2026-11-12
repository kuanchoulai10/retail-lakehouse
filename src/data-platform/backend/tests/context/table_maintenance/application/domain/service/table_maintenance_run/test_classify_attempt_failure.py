"""Test how a failed maintenance attempt is classified from its evidence."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptEnding,
    ContainerExit,
    FailureClass,
    FailureEvidence,
)
from context.table_maintenance.application.domain.service.table_maintenance_run import (
    classify_attempt_failure,
)


def executor(reason: str | None, exit_code: int | None) -> ContainerExit:
    """Build a terminated executor container."""
    return ContainerExit(role="executor", reason=reason, exit_code=exit_code, message=None)


def driver(reason: str | None, exit_code: int | None, message: str | None = None) -> ContainerExit:
    """Build a terminated driver container."""
    return ContainerExit(role="driver", reason=reason, exit_code=exit_code, message=message)


def classify(ended_by: AttemptEnding, *texts: str, containers: tuple[ContainerExit, ...] = ()) -> FailureClass:
    """Classify an attempt from its ending, texts and containers."""
    return classify_attempt_failure(FailureEvidence(ended_by=ended_by, texts=texts, containers=containers))


def test_oom_killed_executor_is_oom() -> None:
    """An executor container killed for memory makes the attempt an OOM."""
    assert classify(AttemptEnding.RESULT, containers=(executor("OOMKilled", 137),)) is FailureClass.OOM


def test_exit_52_executor_is_oom() -> None:
    """Spark's exit code for a JVM OutOfMemoryError on an executor is an OOM."""
    assert classify(AttemptEnding.RESULT, containers=(executor("Error", 52),)) is FailureClass.OOM


def test_exit_137_driver_is_oom() -> None:
    """A driver killed with exit code 137 in a failed job is an OOM."""
    assert classify(AttemptEnding.JOB_FAILED, containers=(driver("Error", 137),)) is FailureClass.OOM


def test_out_of_memory_error_text_is_oom() -> None:
    """A Java OutOfMemoryError in the reported error is an OOM."""
    text = "Py4JJavaError: An error occurred while calling o123.rewrite. java.lang.OutOfMemoryError: Java heap space"
    assert classify(AttemptEnding.RESULT, text) is FailureClass.OOM


def test_oom_killed_in_the_job_error_is_oom() -> None:
    """The job error naming an OOMKilled container is an OOM."""
    assert classify(AttemptEnding.JOB_FAILED, "driver container failed with ExitCode: 137, Reason: OOMKilled") is (
        FailureClass.OOM
    )


def test_exit_code_52_text_is_oom() -> None:
    """A text naming exit code 52 is an OOM."""
    assert classify(AttemptEnding.RESULT, "Executor 1 exited with exit code 52") is FailureClass.OOM


def test_timed_out_attempt_is_timeout_even_with_exit_137() -> None:
    """Pods the platform deleted after a timeout die with 137, which is not an OOM."""
    assert classify(AttemptEnding.TIMED_OUT, containers=(driver("Error", 137), executor("Error", 137))) is (
        FailureClass.TIMEOUT
    )


def test_cancelled_attempt_is_cancelled_even_with_exit_137() -> None:
    """Pods the platform deleted after a cancel die with 137, which is not an OOM."""
    assert classify(AttemptEnding.CANCELLED, containers=(executor("OOMKilled", 137),)) is FailureClass.CANCELLED


def test_exit_137_counts_only_for_result_and_job_failed() -> None:
    """A missing job whose pods died with 137 has no OOM evidence."""
    assert classify(AttemptEnding.MISSING, containers=(executor("Error", 137),)) is FailureClass.OTHER


def test_commit_failed_is_commit_conflict() -> None:
    """A CommitFailedException means another commit won."""
    text = "org.apache.iceberg.exceptions.CommitFailedException: Requirement failed: branch main has changed"
    assert classify(AttemptEnding.RESULT, text) is FailureClass.COMMIT_CONFLICT


def test_missing_table_is_permanent() -> None:
    """A table that does not exist cannot be fixed by a retry."""
    text = "org.apache.iceberg.exceptions.NoSuchTableException: Table does not exist: e2e.orders"
    assert classify(AttemptEnding.RESULT, text) is FailureClass.PERMANENT


def test_missing_permission_is_permanent() -> None:
    """A refused permission cannot be fixed by a retry."""
    assert classify(AttemptEnding.RESULT, "ForbiddenException: Principal is not authorized") is FailureClass.PERMANENT
    assert classify(AttemptEnding.RESULT, "NotAuthorizedException: Not authorized") is FailureClass.PERMANENT


def test_oom_wins_over_commit_conflict() -> None:
    """An attempt that ran out of memory and conflicted is an OOM."""
    texts = ("CommitFailedException: branch main has changed", "java.lang.OutOfMemoryError: GC overhead limit exceeded")
    assert classify(AttemptEnding.RESULT, *texts) is FailureClass.OOM


def test_oom_text_in_a_driver_termination_message_is_oom() -> None:
    """A driver whose termination message holds an OutOfMemoryError is an OOM."""
    container = driver("Error", 1, message="Exception in thread main java.lang.OutOfMemoryError: Java heap space")
    assert classify(AttemptEnding.JOB_FAILED, containers=(container,)) is FailureClass.OOM


def test_partial_progress_with_nothing_committed_is_other() -> None:
    """The runtime's partial-progress message alone is not evidence of a cause."""
    text = "RuntimeError: rewrite_data_files failed: no file group was committed"
    assert classify(AttemptEnding.RESULT, text) is FailureClass.OTHER


def test_unknown_error_is_other() -> None:
    """An error with no known signal is other."""
    assert classify(AttemptEnding.SUBMIT_FAILED, "connection reset by peer") is FailureClass.OTHER
