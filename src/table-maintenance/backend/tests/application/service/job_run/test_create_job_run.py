"""Tests for CreateJobRunService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from core.application.domain.model.job import (
    Job,
    JobId,
    JobNotFoundError,
    JobStatus,
    JobType,
)

from core.application.service.job_run.create_job_run import CreateJobRunService
from core.application.exceptions import JobDisabledError
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import (
    CreateJobRunInput,
    CreateJobRunOutput,
    CreateJobRunUseCase,
)


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
    """Verify that CreateJobRunService implements CreateJobRunUseCase."""
    assert issubclass(CreateJobRunService, CreateJobRunUseCase)


def test_creates_run_for_active_job():
    """Verify that execute creates a job run and returns output for an active job."""
    repo = MagicMock()
    repo.get.return_value = _active_job()
    job_runs_repo = MagicMock()
    job_runs_repo.count_active_for_job.return_value = 0
    job_runs_repo.create.side_effect = lambda run: run
    service = CreateJobRunService(repo, job_runs_repo)

    result = service.execute(CreateJobRunInput(job_id="abc1234567"))

    assert isinstance(result, CreateJobRunOutput)
    job_runs_repo.create.assert_called_once()
    assert result.job_id == "abc1234567"


def test_raises_disabled_when_job_paused():
    """Verify that execute raises JobDisabledError when the job is paused."""
    repo = MagicMock()
    repo.get.return_value = _paused_job()
    job_runs_repo = MagicMock()
    service = CreateJobRunService(repo, job_runs_repo)

    with pytest.raises(JobDisabledError) as exc_info:
        service.execute(CreateJobRunInput(job_id="abc1234567"))
    assert exc_info.value.job_id == "abc1234567"


def test_raises_not_found_when_job_missing():
    """Verify that execute raises AppJobNotFoundError when the job does not exist."""
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("ghost")
    job_runs_repo = MagicMock()
    service = CreateJobRunService(repo, job_runs_repo)

    with pytest.raises(AppJobNotFoundError):
        service.execute(CreateJobRunInput(job_id="ghost"))
