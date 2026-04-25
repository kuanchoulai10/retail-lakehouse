"""Tests for DeleteJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from core.application.domain.model.job import JobId, JobNotFoundError
from core.application.service.job.delete_job import DeleteJobService
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import (
    DeleteJobInput,
    DeleteJobOutput,
    DeleteJobUseCase,
)


def test_delete_job_service_implements_use_case():
    """Verify that DeleteJobService implements DeleteJobUseCase."""
    assert issubclass(DeleteJobService, DeleteJobUseCase)


def test_delete_job_returns_output():
    """Verify that execute returns a DeleteJobOutput and calls repo.delete."""
    repo = MagicMock()
    repo.delete.return_value = None
    service = DeleteJobService(repo)

    result = service.execute(DeleteJobInput(job_id="abc1234567"))

    assert isinstance(result, DeleteJobOutput)
    repo.delete.assert_called_once_with(JobId(value="abc1234567"))


def test_delete_job_raises_app_not_found():
    """Verify that execute raises AppJobNotFoundError when job does not exist."""
    repo = MagicMock()
    repo.delete.side_effect = JobNotFoundError("nonexistent")
    service = DeleteJobService(repo)

    with pytest.raises(AppJobNotFoundError) as exc_info:
        service.execute(DeleteJobInput(job_id="nonexistent"))
    assert exc_info.value.job_id == "nonexistent"
