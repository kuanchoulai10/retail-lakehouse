"""Tests for CreateJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.service.job.create_job import CreateJobService
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)


def _make_service() -> tuple[CreateJobService, MagicMock]:
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    service = CreateJobService(repo)
    return service, repo


def test_create_job_service_implements_use_case():
    assert issubclass(CreateJobService, CreateJobUseCase)


def test_create_job_returns_output():
    service, _ = _make_service()

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    result = service.execute(input_)

    assert isinstance(result, CreateJobOutput)
    assert result.job_type == "rewrite_data_files"
    assert result.enabled is False


def test_create_job_populates_domain_fields():
    service, repo = _make_service()

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


def test_create_job_enabled_defaults_to_false():
    service, repo = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
        )
    )

    job = repo.create.call_args[0][0]
    assert job.enabled is False


def test_create_job_enabled_passed_through_from_input():
    service, repo = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
            enabled=True,
        )
    )

    job = repo.create.call_args[0][0]
    assert job.enabled is True


def test_create_job_sets_updated_at_equal_to_created_at_initially():
    service, repo = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
        )
    )

    job = repo.create.call_args[0][0]
    assert job.updated_at == job.created_at


def test_create_job_extracts_table_from_expire_snapshots():
    service, repo = _make_service()

    input_ = CreateJobInput(
        job_type="expire_snapshots",
        catalog="retail",
        expire_snapshots={"table": "inventory.orders"},
    )
    service.execute(input_)

    job = repo.create.call_args[0][0]
    assert job.table == "inventory.orders"
    assert job.job_config == {"table": "inventory.orders"}
