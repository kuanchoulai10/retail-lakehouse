"""Tests for CreateJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.port.inbound import CreateJobInput, CreateJobOutput, CreateJobUseCase


def test_create_job_service_implements_use_case():
    assert issubclass(CreateJobService, CreateJobUseCase)


def test_create_job_returns_output():
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    service = CreateJobService(repo)

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files={"table": "inventory.orders"},
    )
    result = service.execute(input_)

    assert isinstance(result, CreateJobOutput)
    assert result.job_type == "rewrite_data_files"
    assert result.status == "pending"
    repo.create.assert_called_once()
