from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.domain.model.job import JobId
from application.domain.model.job_run import (
    JobRun,
    JobRunId,
    JobRunNotFoundError,
    JobRunStatus,
)
from application.domain.service.get_job_run import GetJobRunService
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound import (
    GetJobRunInput,
    GetJobRunOutput,
    GetJobRunUseCase,
)


def test_implements_use_case():
    assert issubclass(GetJobRunService, GetJobRunUseCase)


def test_get_returns_run():
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
    repo = MagicMock()
    repo.get.side_effect = JobRunNotFoundError("ghost")
    service = GetJobRunService(repo)

    with pytest.raises(AppJobRunNotFoundError) as exc_info:
        service.execute(GetJobRunInput(run_id="ghost"))
    assert exc_info.value.run_id == "ghost"
