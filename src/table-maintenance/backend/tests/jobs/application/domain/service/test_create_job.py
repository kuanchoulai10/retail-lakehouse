"""Tests for CreateJob use case service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from jobs.application.domain.job import Job
from jobs.application.domain.job_id import JobId
from jobs.application.domain.job_status import JobStatus
from jobs.application.domain.job_type import JobType
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.port.inbound import CreateJobInput, CreateJobOutput, CreateJobUseCase


def _make_job() -> Job:
    return Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.PENDING,
        created_at=datetime(2026, 4, 11, tzinfo=UTC),
    )


def test_create_job_service_implements_use_case():
    assert issubclass(CreateJobService, CreateJobUseCase)


def test_create_job_returns_output():
    repo = MagicMock()
    repo.create.return_value = _make_job()
    service = CreateJobService(repo)

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files={"table": "inventory.orders"},
    )
    result = service.execute(input_)

    assert isinstance(result, CreateJobOutput)
    assert result.id == "abc1234567"
    assert result.job_type == "rewrite_data_files"
    assert result.status == "pending"
    repo.create.assert_called_once()
