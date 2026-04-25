"""Tests for GetJob use case service."""

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
from core.application.service.job.get_job import GetJobService
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import GetJobInput, GetJobOutput, GetJobUseCase


def _make_job(job_id: str = "abc1234567") -> Job:
    """Provide a Job domain entity with sensible defaults."""
    ts = datetime(2026, 4, 10, tzinfo=UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=ts,
        updated_at=ts,
        status=JobStatus.ACTIVE,
    )


def test_get_job_service_implements_use_case():
    """Verify that GetJobService implements GetJobUseCase."""
    assert issubclass(GetJobService, GetJobUseCase)


def test_get_job_returns_result():
    """Verify that execute returns a GetJobOutput with correct fields."""
    repo = MagicMock()
    repo.get.return_value = _make_job()
    service = GetJobService(repo)

    result = service.execute(GetJobInput(job_id="abc1234567"))

    assert isinstance(result, GetJobOutput)
    assert result.id == "abc1234567"
    assert result.job_type == "rewrite_data_files"
    assert result.status == "active"
    repo.get.assert_called_once_with(JobId(value="abc1234567"))


def test_get_job_raises_app_not_found():
    """Verify that execute raises AppJobNotFoundError when job does not exist."""
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("nonexistent")
    service = GetJobService(repo)

    with pytest.raises(AppJobNotFoundError) as exc_info:
        service.execute(GetJobInput(job_id="nonexistent"))
    assert exc_info.value.job_id == "nonexistent"
