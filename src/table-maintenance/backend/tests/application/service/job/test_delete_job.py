"""Tests for archive-job flow via UpdateJobService with status='archived'."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.domain.model.job import (
    Job,
    JobId,
    JobNotFoundError,
    JobStatus,
    JobType,
    TableReference,
)
from application.service.job.update_job import UpdateJobService
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    UpdateJobInput,
    UpdateJobOutput,
)


def _existing_job() -> Job:
    """Provide an existing active Job domain entity for archive tests."""
    return Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        cron=None,
        status=JobStatus.ACTIVE,
    )


def test_archive_job_returns_output():
    """Verify that archiving via UpdateJobService returns an UpdateJobOutput with archived status."""
    repo = MagicMock()
    repo.get.return_value = _existing_job()
    repo.update.side_effect = lambda job: job
    outbox_repo = MagicMock()
    serializer = MagicMock()
    serializer.to_outbox_entries.return_value = []
    service = UpdateJobService(repo, outbox_repo, serializer)

    result = service.execute(UpdateJobInput(job_id="abc1234567", status="archived"))

    assert isinstance(result, UpdateJobOutput)
    assert result.status == "archived"
    repo.update.assert_called_once()


def test_archive_job_raises_app_not_found():
    """Verify that archiving raises AppJobNotFoundError when job does not exist."""
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("nonexistent")
    outbox_repo = MagicMock()
    serializer = MagicMock()
    serializer.to_outbox_entries.return_value = []
    service = UpdateJobService(repo, outbox_repo, serializer)

    with pytest.raises(AppJobNotFoundError) as exc_info:
        service.execute(UpdateJobInput(job_id="nonexistent", status="archived"))
    assert exc_info.value.job_id == "nonexistent"
