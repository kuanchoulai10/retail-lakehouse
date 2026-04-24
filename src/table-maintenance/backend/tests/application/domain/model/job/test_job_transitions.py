"""Tests for Job state transitions and trigger behavior."""

from datetime import UTC, datetime

import pytest

from application.domain.model.job import (
    InvalidJobStateTransitionError,
    Job,
    JobId,
    JobNotActiveError,
    JobStatus,
    JobType,
    MaxActiveRunsExceededError,
)
from application.domain.model.job_run import JobRunId, JobRunStatus

NOW = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)


def _make_job(status: JobStatus = JobStatus.ACTIVE) -> Job:
    """Create a Job with the given status for testing."""
    return Job(
        id=JobId(value="job-1"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=NOW,
        updated_at=NOW,
        status=status,
    )


class TestPause:
    """Tests for Job.pause()."""

    def test_active_to_paused(self):
        """Verify ACTIVE job can be paused."""
        job = _make_job(JobStatus.ACTIVE)
        job.pause()
        assert job.status == JobStatus.PAUSED

    def test_archived_to_paused_raises(self):
        """Verify ARCHIVED job cannot be paused."""
        job = _make_job(JobStatus.ARCHIVED)
        with pytest.raises(InvalidJobStateTransitionError):
            job.pause()


class TestResume:
    """Tests for Job.resume()."""

    def test_paused_to_active(self):
        """Verify PAUSED job can be resumed."""
        job = _make_job(JobStatus.PAUSED)
        job.resume()
        assert job.status == JobStatus.ACTIVE

    def test_active_to_active_raises(self):
        """Verify ACTIVE job cannot be resumed (already active)."""
        job = _make_job(JobStatus.ACTIVE)
        with pytest.raises(InvalidJobStateTransitionError):
            job.resume()


class TestArchive:
    """Tests for Job.archive()."""

    def test_active_to_archived(self):
        """Verify ACTIVE job can be archived."""
        job = _make_job(JobStatus.ACTIVE)
        job.archive()
        assert job.status == JobStatus.ARCHIVED

    def test_paused_to_archived(self):
        """Verify PAUSED job can be archived."""
        job = _make_job(JobStatus.PAUSED)
        job.archive()
        assert job.status == JobStatus.ARCHIVED


class TestTrigger:
    """Tests for Job.trigger()."""

    def test_creates_pending_run(self):
        """Verify trigger creates a PENDING JobRun."""
        job = _make_job(JobStatus.ACTIVE)
        run = job.trigger(
            run_id=JobRunId(value="run-1"),
            now=NOW,
            active_run_count=0,
        )
        assert run.id == JobRunId(value="run-1")
        assert run.job_id == job.id
        assert run.status == JobRunStatus.PENDING
        assert run.started_at == NOW

    def test_raises_when_not_active(self):
        """Verify trigger raises JobNotActiveError for paused job."""
        job = _make_job(JobStatus.PAUSED)
        with pytest.raises(JobNotActiveError):
            job.trigger(
                run_id=JobRunId(value="run-1"),
                now=NOW,
                active_run_count=0,
            )

    def test_raises_when_max_active_runs_exceeded(self):
        """Verify trigger raises MaxActiveRunsExceededError."""
        job = _make_job(JobStatus.ACTIVE)
        job.max_active_runs = 1
        with pytest.raises(MaxActiveRunsExceededError):
            job.trigger(
                run_id=JobRunId(value="run-1"),
                now=NOW,
                active_run_count=1,
            )

    def test_allows_trigger_under_max_active_runs(self):
        """Verify trigger succeeds when active count < max."""
        job = _make_job(JobStatus.ACTIVE)
        job.max_active_runs = 3
        run = job.trigger(
            run_id=JobRunId(value="run-1"),
            now=NOW,
            active_run_count=2,
        )
        assert run.status == JobRunStatus.PENDING


class TestIsActive:
    """Tests for Job.is_active property."""

    def test_active_is_true(self):
        """Verify is_active returns True for ACTIVE jobs."""
        assert _make_job(JobStatus.ACTIVE).is_active is True

    def test_paused_is_false(self):
        """Verify is_active returns False for PAUSED jobs."""
        assert _make_job(JobStatus.PAUSED).is_active is False

    def test_archived_is_false(self):
        """Verify is_active returns False for ARCHIVED jobs."""
        assert _make_job(JobStatus.ARCHIVED).is_active is False
