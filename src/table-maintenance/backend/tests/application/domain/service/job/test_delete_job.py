"""Tests for DeleteJob use case service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from application.domain.model.job import JobId, JobNotFoundError
from application.domain.service.job.delete_job import DeleteJobService
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    DeleteJobInput,
    DeleteJobOutput,
    DeleteJobUseCase,
)


def test_delete_job_service_implements_use_case():
    assert issubclass(DeleteJobService, DeleteJobUseCase)


def test_delete_job_returns_output():
    repo = MagicMock()
    repo.delete.return_value = None
    service = DeleteJobService(repo)

    result = service.execute(DeleteJobInput(job_id="abc1234567"))

    assert isinstance(result, DeleteJobOutput)
    repo.delete.assert_called_once_with(JobId(value="abc1234567"))


def test_delete_job_raises_app_not_found():
    repo = MagicMock()
    repo.delete.side_effect = JobNotFoundError("nonexistent")
    service = DeleteJobService(repo)

    with pytest.raises(AppJobNotFoundError) as exc_info:
        service.execute(DeleteJobInput(job_id="nonexistent"))
    assert exc_info.value.job_id == "nonexistent"
