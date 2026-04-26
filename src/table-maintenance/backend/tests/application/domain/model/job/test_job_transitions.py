"""Tests for Job state transitions and trigger behavior."""

from datetime import UTC, datetime

import pytest

from application.domain.model.job import (
    CronExpression,
    InvalidJobStateTransitionError,
    Job,
    JobId,
    JobNotActiveError,
    JobStatus,
    JobType,
    MaxActiveRunsExceededError,
    TableReference,
)
from application.domain.model.job.events import (
    JobArchived,
    JobPaused,
    JobResumed,
    JobTriggered,
    JobUpdated,
)
from application.domain.model.job_run import TriggerType

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

    def test_pause_registers_event(self):
        """Verify pause() registers a JobPaused event."""
        job = _make_job(JobStatus.ACTIVE)
        job.pause()
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobPaused)
        assert events[0].job_id == JobId(value="job-1")


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

    def test_resume_registers_event(self):
        """Verify resume() registers a JobResumed event."""
        job = _make_job(JobStatus.PAUSED)
        job.resume()
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobResumed)
        assert events[0].job_id == JobId(value="job-1")


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

    def test_archive_registers_event(self):
        """Verify archive() registers a JobArchived event."""
        job = _make_job(JobStatus.ACTIVE)
        job.archive()
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobArchived)
        assert events[0].job_id == JobId(value="job-1")


class TestTrigger:
    """Tests for Job.trigger()."""

    def test_registers_job_triggered_event(self):
        """Verify trigger registers a JobTriggered event."""
        job = _make_job(JobStatus.ACTIVE)
        job.trigger(active_run_count=0)
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobTriggered)
        assert events[0].job_id == JobId(value="job-1")
        assert events[0].trigger_type == TriggerType.MANUAL

    def test_trigger_with_scheduled_type(self):
        """Verify trigger passes through trigger_type."""
        job = _make_job(JobStatus.ACTIVE)
        job.trigger(active_run_count=0, trigger_type=TriggerType.SCHEDULED)
        events = job.collect_events()
        event = events[0]
        assert isinstance(event, JobTriggered)
        assert event.trigger_type == TriggerType.SCHEDULED

    def test_raises_when_not_active(self):
        """Verify trigger raises JobNotActiveError for paused job."""
        job = _make_job(JobStatus.PAUSED)
        with pytest.raises(JobNotActiveError):
            job.trigger(active_run_count=0)

    def test_raises_when_max_active_runs_exceeded(self):
        """Verify trigger raises MaxActiveRunsExceededError."""
        job = _make_job(JobStatus.ACTIVE)
        job.max_active_runs = 1
        with pytest.raises(MaxActiveRunsExceededError):
            job.trigger(active_run_count=1)

    def test_no_event_on_failure(self):
        """Verify no event is registered when trigger fails."""
        job = _make_job(JobStatus.PAUSED)
        with pytest.raises(JobNotActiveError):
            job.trigger(active_run_count=0)
        assert job.collect_events() == []


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


class TestApplyChanges:
    """Tests for Job.apply_changes()."""

    def test_change_cron(self):
        """Verify changing cron registers JobUpdated with FieldChange."""
        job = _make_job(JobStatus.ACTIVE)
        old_cron = CronExpression(expression="0 * * * *")
        new_cron = CronExpression(expression="0 2 * * *")
        job.cron = old_cron
        job.apply_changes(cron=new_cron)
        assert job.cron == new_cron
        events = job.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, JobUpdated)
        assert len(event.changes) == 1
        assert event.changes[0].field == "cron"

    def test_change_table_ref(self):
        """Verify changing table_ref registers JobUpdated."""
        job = _make_job(JobStatus.ACTIVE)
        new_ref = TableReference(catalog="new_cat", table="new_tbl")
        job.apply_changes(table_ref=new_ref)
        assert job.table_ref == new_ref
        events = job.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, JobUpdated)
        assert event.changes[0].field == "table_ref"

    def test_change_job_config(self):
        """Verify changing job_config registers JobUpdated."""
        job = _make_job(JobStatus.ACTIVE)
        job.apply_changes(job_config={"new_key": True})
        assert job.job_config == {"new_key": True}
        events = job.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, JobUpdated)
        assert event.changes[0].field == "job_config"

    def test_multiple_changes(self):
        """Verify multiple field changes produce one event with multiple FieldChanges."""
        job = _make_job(JobStatus.ACTIVE)
        new_cron = CronExpression(expression="0 3 * * *")
        new_ref = TableReference(catalog="c", table="t")
        job.apply_changes(cron=new_cron, table_ref=new_ref)
        events = job.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, JobUpdated)
        assert len(event.changes) == 2

    def test_no_change_no_event(self):
        """Verify no event is registered when values are unchanged."""
        job = _make_job(JobStatus.ACTIVE)
        job.apply_changes(table_ref=job.table_ref)
        assert job.collect_events() == []

    def test_none_args_ignored(self):
        """Verify None arguments are ignored (no changes applied)."""
        job = _make_job(JobStatus.ACTIVE)
        job.apply_changes()
        assert job.collect_events() == []
