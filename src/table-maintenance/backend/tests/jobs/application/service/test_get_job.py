"""Tests for GetJob use case service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from jobs.application.exceptions import JobNotFoundError as AppJobNotFoundError
from jobs.application.port.inbound.get_job import GetJobResult, GetJobUseCase
from jobs.application.service.get_job import GetJobService
from jobs.domain.exceptions import JobNotFoundError
from jobs.domain.job import Job
from jobs.domain.job_id import JobId
from jobs.domain.job_status import JobStatus
from jobs.domain.job_type import JobType


def _make_job(job_id: str = "abc1234567") -> Job:
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
    )


def test_get_job_service_implements_use_case():
    assert issubclass(GetJobService, GetJobUseCase)


def test_get_job_returns_result():
    repo = MagicMock()
    repo.get.return_value = _make_job()
    service = GetJobService(repo)

    result = service.execute("abc1234567")

    assert isinstance(result, GetJobResult)
    assert result.id == "abc1234567"
    assert result.job_type == "rewrite_data_files"
    assert result.status == "completed"
    repo.get.assert_called_once_with("abc1234567")


def test_get_job_raises_app_not_found():
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("nonexistent")
    service = GetJobService(repo)

    with pytest.raises(AppJobNotFoundError) as exc_info:
        service.execute("nonexistent")
    assert exc_info.value.job_id == "nonexistent"
