"""Tests for CreateJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.service.create_job import CreateJobService
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)


def _make_service() -> tuple[CreateJobService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.create.side_effect = lambda job: job
    executor = MagicMock()
    service = CreateJobService(repo, executor)
    return service, repo, executor


def test_create_job_service_implements_use_case():
    assert issubclass(CreateJobService, CreateJobUseCase)


def test_create_job_returns_output():
    service, _, _ = _make_service()

    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    result = service.execute(input_)

    assert isinstance(result, CreateJobOutput)
    assert result.job_type == "rewrite_data_files"
    assert result.status == "pending"


def test_create_job_populates_domain_fields():
    service, repo, _ = _make_service()

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


def test_create_job_sets_enabled_true_for_transitional_behavior():
    """During the Job/JobRun split transition, service hardcodes enabled=True
    so POST /jobs still triggers K8s — preserving the pre-split API behavior.
    Stage 7 will flip this default to False and gate on input.enabled."""
    service, repo, _ = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
        )
    )

    job = repo.create.call_args[0][0]
    assert job.enabled is True


def test_create_job_sets_updated_at_equal_to_created_at_initially():
    service, repo, _ = _make_service()

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
    service, repo, _ = _make_service()

    input_ = CreateJobInput(
        job_type="expire_snapshots",
        catalog="retail",
        expire_snapshots={"table": "inventory.orders"},
    )
    service.execute(input_)

    job = repo.create.call_args[0][0]
    assert job.table == "inventory.orders"
    assert job.job_config == {"table": "inventory.orders"}


def test_create_job_triggers_executor_after_repo_create_when_enabled():
    service, repo, executor = _make_service()

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
        )
    )

    repo.create.assert_called_once()
    executor.trigger.assert_called_once()
    # Executor receives the same Job instance that was saved
    saved_job = repo.create.call_args[0][0]
    triggered_job = executor.trigger.call_args[0][0]
    assert triggered_job is saved_job


def test_create_job_does_not_trigger_executor_if_job_disabled():
    """Defense-in-depth: if a future change somewhere sets enabled=False,
    the service must not call the executor."""
    repo = MagicMock()
    # Repo simulates persistence flipping enabled off
    repo.create.side_effect = lambda job: type(job)(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        catalog=job.catalog,
        table=job.table,
        job_config=job.job_config,
        cron=job.cron,
        enabled=False,
    )
    executor = MagicMock()
    service = CreateJobService(repo, executor)

    service.execute(
        CreateJobInput(
            job_type="rewrite_data_files",
            catalog="retail",
            rewrite_data_files={"table": "inventory.orders"},
        )
    )

    executor.trigger.assert_not_called()
