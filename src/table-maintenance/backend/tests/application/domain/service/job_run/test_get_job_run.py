"""Tests for GetJobRunService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from core.application.domain.model.job import JobId
from core.application.domain.model.job_run import (
    JobRun,
    JobRunId,
    JobRunNotFoundError,
    JobRunStatus,
)
from core.application.service.job_run.get_job_run import GetJobRunService
from core.application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from core.application.port.inbound import (
    GetJobRunInput,
    GetJobRunOutput,
    GetJobRunUseCase,
)


def test_implements_use_case():
    """Verify that GetJobRunService implements GetJobRunUseCase."""
    assert issubclass(GetJobRunService, GetJobRunUseCase)


def test_get_returns_run():
    """Verify that execute returns a GetJobRunOutput with correct fields."""
    repo = MagicMock()
    repo.get.return_value = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.COMPLETED,
        started_at=datetime.now(UTC),
    )
    service = GetJobRunService(repo)

    result = service.execute(GetJobRunInput(run_id="run-1"))

    assert isinstance(result, GetJobRunOutput)
    assert result.run_id == "run-1"
    assert result.job_id == "job-1"
    assert result.status == "completed"


def test_get_raises_app_not_found():
    """Verify that execute raises AppJobRunNotFoundError when run does not exist."""
    repo = MagicMock()
    repo.get.side_effect = JobRunNotFoundError("ghost")
    service = GetJobRunService(repo)

    with pytest.raises(AppJobRunNotFoundError) as exc_info:
        service.execute(GetJobRunInput(run_id="ghost"))
    assert exc_info.value.run_id == "ghost"
