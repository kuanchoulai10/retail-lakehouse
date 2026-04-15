"""Tests for CreateJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.service.create_job import CreateJobService
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)


def test_create_job_service_implements_use_case():
    assert issubclass(CreateJobService, CreateJobUseCase)


def test_create_job_returns_output():
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    service = CreateJobService(repo)

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    result = service.execute(input_)

    assert isinstance(result, CreateJobOutput)
    assert result.job_type == "rewrite_data_files"
    assert result.status == "pending"
    repo.create.assert_called_once()


def test_create_job_populates_domain_fields():
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    service = CreateJobService(repo)

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders", "rewrite_all": True},
        cron="0 2 * * *",
    )
    service.execute(input_)

    job = repo.create.call_args[0][0]
    assert job.catalog == "retail"
    assert job.table == "inventory.orders"
    assert job.job_config == {"table": "inventory.orders", "rewrite_all": True}
    assert job.cron == "0 2 * * *"


def test_create_job_extracts_table_from_expire_snapshots():
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    service = CreateJobService(repo)

    input_ = CreateJobInput(
        job_type="expire_snapshots",
        catalog="retail",
        expire_snapshots={"table": "inventory.orders"},
    )
    service.execute(input_)

    job = repo.create.call_args[0][0]
    assert job.table == "inventory.orders"
    assert job.job_config == {"table": "inventory.orders"}
