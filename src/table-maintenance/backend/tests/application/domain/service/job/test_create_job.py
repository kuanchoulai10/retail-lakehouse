"""Tests for CreateJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.model.job import JobStatus
from application.domain.service.job.create_job import CreateJobService
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)


def _make_service() -> tuple[CreateJobService, MagicMock]:
    """Provide a CreateJobService with a mocked repository."""
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    service = CreateJobService(repo)
    return service, repo


def test_create_job_service_implements_use_case():
    """Verify that CreateJobService implements CreateJobUseCase."""
    assert issubclass(CreateJobService, CreateJobUseCase)


def test_create_job_returns_output():
    """Verify that execute returns a CreateJobOutput with correct fields."""
    service, _ = _make_service()

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    result = service.execute(input_)

    assert isinstance(result, CreateJobOutput)
    assert result.job_type == "rewrite_data_files"
    assert result.status == "active"


def test_create_job_populates_domain_fields():
    """Verify that execute populates catalog, table, job_config, and cron on the domain entity."""
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


def test_create_job_status_defaults_to_active():
    """Verify that status defaults to active when not provided."""
    service, repo = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
        )
    )

    job = repo.create.call_args[0][0]
    assert job.status == JobStatus.ACTIVE


def test_create_job_status_passed_through_from_input():
    """Verify that status is passed through from input when explicitly set."""
    service, repo = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
            status="paused",
        )
    )

    job = repo.create.call_args[0][0]
    assert job.status == JobStatus.PAUSED


def test_create_job_sets_updated_at_equal_to_created_at_initially():
    """Verify that updated_at equals created_at on initial creation."""
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
    """Verify that table is extracted from expire_snapshots config."""
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
