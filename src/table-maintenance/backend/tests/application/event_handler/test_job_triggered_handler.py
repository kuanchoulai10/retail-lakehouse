"""Tests for JobTriggeredHandler."""

from unittest.mock import MagicMock

from core.application.domain.model.job import JobId
from core.application.domain.model.job.events import JobTriggered
from core.application.domain.model.job_run import JobRunStatus, TriggerType
from core.application.event_handler.job_triggered_handler import JobTriggeredHandler


def test_creates_pending_job_run():
    """Verify handler creates a PENDING JobRun and persists it."""
    repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo=repo)
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
    )
    handler.handle(event)
    repo.create.assert_called_once()
    run = repo.create.call_args[0][0]
    assert run.job_id == JobId(value="j1")
    assert run.status == JobRunStatus.PENDING
    assert run.trigger_type == TriggerType.MANUAL
    assert run.id.value.startswith("j1-")


def test_creates_scheduled_run():
    """Verify handler passes through SCHEDULED trigger type."""
    repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo=repo)
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.SCHEDULED,
    )
    handler.handle(event)
    run = repo.create.call_args[0][0]
    assert run.trigger_type == TriggerType.SCHEDULED


def test_exposes_last_created_run():
    """Verify handler exposes the created run via last_created_run."""
    repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo=repo)
    assert handler.last_created_run is None
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
    )
    handler.handle(event)
    assert handler.last_created_run is not None
    assert handler.last_created_run.job_id == JobId(value="j1")
