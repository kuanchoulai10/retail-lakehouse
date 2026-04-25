"""Tests for JobRun state transition methods."""

from datetime import UTC, datetime

import pytest

from core.application.domain.model.job import JobId
from core.application.domain.model.job_run import (
    InvalidStateTransitionError,
    JobRun,
    JobRunId,
    JobRunStatus,
)


def _make_run(status: JobRunStatus = JobRunStatus.PENDING) -> JobRun:
    """Create a JobRun with the given status for testing."""
    return JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=status,
    )


class TestMarkRunning:
    """Tests for JobRun.mark_running()."""

    def test_pending_to_running(self):
        """Verify PENDING run transitions to RUNNING with started_at set."""
        run = _make_run(JobRunStatus.PENDING)
        now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
        run.mark_running(now)
        assert run.status == JobRunStatus.RUNNING
        assert run.started_at == now

    def test_completed_to_running_raises(self):
        """Verify COMPLETED run cannot transition to RUNNING."""
        run = _make_run(JobRunStatus.COMPLETED)
        with pytest.raises(InvalidStateTransitionError):
            run.mark_running(datetime.now(UTC))

    def test_failed_to_running_raises(self):
        """Verify FAILED run cannot transition to RUNNING."""
        run = _make_run(JobRunStatus.FAILED)
        with pytest.raises(InvalidStateTransitionError):
            run.mark_running(datetime.now(UTC))


class TestMarkCompleted:
    """Tests for JobRun.mark_completed()."""

    def test_running_to_completed(self):
        """Verify RUNNING run transitions to COMPLETED with finished_at set."""
        run = _make_run(JobRunStatus.RUNNING)
        now = datetime(2026, 4, 25, 13, 0, tzinfo=UTC)
        run.mark_completed(now)
        assert run.status == JobRunStatus.COMPLETED
        assert run.finished_at == now

    def test_pending_to_completed_raises(self):
        """Verify PENDING run cannot skip to COMPLETED."""
        run = _make_run(JobRunStatus.PENDING)
        with pytest.raises(InvalidStateTransitionError):
            run.mark_completed(datetime.now(UTC))


class TestMarkFailed:
    """Tests for JobRun.mark_failed()."""

    def test_pending_to_failed(self):
        """Verify PENDING run can transition to FAILED."""
        run = _make_run(JobRunStatus.PENDING)
        now = datetime(2026, 4, 25, 14, 0, tzinfo=UTC)
        run.mark_failed(now)
        assert run.status == JobRunStatus.FAILED
        assert run.finished_at == now

    def test_running_to_failed(self):
        """Verify RUNNING run can transition to FAILED."""
        run = _make_run(JobRunStatus.RUNNING)
        now = datetime(2026, 4, 25, 14, 0, tzinfo=UTC)
        run.mark_failed(now)
        assert run.status == JobRunStatus.FAILED
        assert run.finished_at == now

    def test_completed_to_failed_raises(self):
        """Verify COMPLETED run cannot transition to FAILED."""
        run = _make_run(JobRunStatus.COMPLETED)
        with pytest.raises(InvalidStateTransitionError):
            run.mark_failed(datetime.now(UTC))


class TestCancel:
    """Tests for JobRun.cancel()."""

    def test_pending_to_cancelled(self):
        """Verify PENDING run can be cancelled."""
        run = _make_run(JobRunStatus.PENDING)
        run.cancel()
        assert run.status == JobRunStatus.CANCELLED

    def test_running_to_cancelled(self):
        """Verify RUNNING run can be cancelled."""
        run = _make_run(JobRunStatus.RUNNING)
        run.cancel()
        assert run.status == JobRunStatus.CANCELLED

    def test_completed_to_cancelled_raises(self):
        """Verify COMPLETED run cannot be cancelled."""
        run = _make_run(JobRunStatus.COMPLETED)
        with pytest.raises(InvalidStateTransitionError):
            run.cancel()

    def test_failed_to_cancelled_raises(self):
        """Verify FAILED run cannot be cancelled."""
        run = _make_run(JobRunStatus.FAILED)
        with pytest.raises(InvalidStateTransitionError):
            run.cancel()
