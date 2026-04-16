from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.domain.model.exceptions import JobNotFoundError
from application.domain.model.job import Job
from application.domain.model.job_id import JobId
from application.domain.model.job_run import JobRun
from application.domain.model.job_run_id import JobRunId
from application.domain.model.job_run_status import JobRunStatus
from application.domain.model.job_type import JobType
from application.domain.service.create_job_run import CreateJobRunService
from application.exceptions import JobDisabledError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    CreateJobRunInput,
    CreateJobRunOutput,
    CreateJobRunUseCase,
)


def _enabled_job(job_id: str = "abc1234567") -> Job:
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        enabled=True,
    )


def _disabled_job(job_id: str = "abc1234567") -> Job:
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        enabled=False,
    )


def _run_for(job_id: str) -> JobRun:
    return JobRun(
        id=JobRunId(value=f"{job_id}-xyz"),
        job_id=JobId(value=job_id),
        status=JobRunStatus.PENDING,
        started_at=datetime.now(UTC),
    )


def test_implements_use_case():
    assert issubclass(CreateJobRunService, CreateJobRunUseCase)


def test_triggers_executor_for_enabled_job():
    repo = MagicMock()
    repo.get.return_value = _enabled_job()
    executor = MagicMock()
    executor.trigger.return_value = _run_for("abc1234567")
    service = CreateJobRunService(repo, executor)

    result = service.execute(CreateJobRunInput(job_id="abc1234567"))

    assert isinstance(result, CreateJobRunOutput)
    executor.trigger.assert_called_once()
    assert result.job_id == "abc1234567"


def test_raises_disabled_when_job_disabled():
    repo = MagicMock()
    repo.get.return_value = _disabled_job()
    executor = MagicMock()
    service = CreateJobRunService(repo, executor)

    with pytest.raises(JobDisabledError) as exc_info:
        service.execute(CreateJobRunInput(job_id="abc1234567"))
    assert exc_info.value.job_id == "abc1234567"
    executor.trigger.assert_not_called()


def test_raises_not_found_when_job_missing():
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("ghost")
    executor = MagicMock()
    service = CreateJobRunService(repo, executor)

    with pytest.raises(AppJobNotFoundError):
        service.execute(CreateJobRunInput(job_id="ghost"))
    executor.trigger.assert_not_called()
