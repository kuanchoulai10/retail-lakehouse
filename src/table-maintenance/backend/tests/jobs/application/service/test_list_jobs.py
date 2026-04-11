"""Tests for ListJobs use case service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from jobs.application.domain.job import Job
from jobs.application.domain.job_id import JobId
from jobs.application.domain.job_status import JobStatus
from jobs.application.domain.job_type import JobType
from jobs.application.port.inbound import ListJobsInput, ListJobsOutput, ListJobsOutputItem, ListJobsUseCase
from jobs.application.service.list_jobs import ListJobsService


def _make_job(job_id: str = "abc1234567") -> Job:
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=datetime(2026, 4, 11, tzinfo=UTC),
    )


def test_list_jobs_service_implements_use_case():
    assert issubclass(ListJobsService, ListJobsUseCase)


def test_list_jobs_returns_output():
    repo = MagicMock()
    repo.list_all.return_value = [_make_job("aaa"), _make_job("bbb")]
    service = ListJobsService(repo)

    result = service.execute(ListJobsInput())

    assert isinstance(result, ListJobsOutput)
    assert len(result.jobs) == 2
    assert isinstance(result.jobs[0], ListJobsOutputItem)
    assert result.jobs[0].id == "aaa"
    assert result.jobs[1].id == "bbb"


def test_list_jobs_empty():
    repo = MagicMock()
    repo.list_all.return_value = []
    service = ListJobsService(repo)

    result = service.execute(ListJobsInput())

    assert result.jobs == []
