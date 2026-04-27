"""Tests for TriggerJobRunService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.domain.model.job import (
    Job,
    JobId,
    JobNotFoundError,
    JobStatus,
    JobType,
)

from application.service.job_run.trigger_job_run import TriggerJobRunService
from application.exceptions import JobDisabledError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    TriggerJobRunInput,
    TriggerJobRunUseCase,
)
from application.port.inbound.job_run.trigger_job_run import TriggerJobRunOutput


def _active_job(job_id: str = "abc1234567") -> Job:
    """Provide an active Job domain entity."""
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        status=JobStatus.ACTIVE,
    )


def _paused_job(job_id: str = "abc1234567") -> Job:
    """Provide a paused Job domain entity."""
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        status=JobStatus.PAUSED,
    )


def test_implements_use_case():
    """Verify that TriggerJobRunService implements TriggerJobRunUseCase."""
    assert issubclass(TriggerJobRunService, TriggerJobRunUseCase)


def _make_service():
    """Provide a TriggerJobRunService with mocked collaborators."""
    repo = MagicMock()
    job_runs_repo = MagicMock()
    outbox_repo = MagicMock()
    serializer = MagicMock()
    serializer.to_outbox_entries.return_value = []
    service = TriggerJobRunService(repo, job_runs_repo, outbox_repo, serializer)
    return service, repo, job_runs_repo


def test_creates_run_for_active_job():
    """Verify that execute triggers a job and returns TriggerJobRunOutput for an active job."""
    service, repo, job_runs_repo = _make_service()
    repo.get.return_value = _active_job()
    job_runs_repo.count_active_for_job.return_value = 0

    result = service.execute(TriggerJobRunInput(job_id="abc1234567"))

    assert isinstance(result, TriggerJobRunOutput)
    assert result.job_id == "abc1234567"
    assert result.accepted is True


def test_raises_disabled_when_job_paused():
    """Verify that execute raises JobDisabledError when the job is paused."""
    service, repo, job_runs_repo = _make_service()
    repo.get.return_value = _paused_job()

    with pytest.raises(JobDisabledError) as exc_info:
        service.execute(TriggerJobRunInput(job_id="abc1234567"))
    assert exc_info.value.job_id == "abc1234567"


def test_raises_not_found_when_job_missing():
    """Verify that execute raises AppJobNotFoundError when the job does not exist."""
    service, repo, job_runs_repo = _make_service()
    repo.get.side_effect = JobNotFoundError("ghost")

    with pytest.raises(AppJobNotFoundError):
        service.execute(TriggerJobRunInput(job_id="ghost"))
