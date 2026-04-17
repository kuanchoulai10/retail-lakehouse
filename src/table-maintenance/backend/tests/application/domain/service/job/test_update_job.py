from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.domain.model.job import Job, JobId, JobNotFoundError, JobType
from application.domain.service.job.update_job import UpdateJobService
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import UpdateJobInput, UpdateJobOutput, UpdateJobUseCase


def _existing_job() -> Job:
    return Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        catalog="retail",
        table="inventory.orders",
        cron=None,
        enabled=False,
    )


def test_implements_use_case():
    assert issubclass(UpdateJobService, UpdateJobUseCase)


def test_update_enables_job():
    repo = MagicMock()
    repo.get.return_value = _existing_job()
    repo.update.side_effect = lambda job: job
    service = UpdateJobService(repo)

    result = service.execute(UpdateJobInput(job_id="abc1234567", enabled=True))

    assert isinstance(result, UpdateJobOutput)
    assert result.enabled is True
    repo.update.assert_called_once()


def test_update_leaves_other_fields_when_only_enabled_provided():
    repo = MagicMock()
    job = _existing_job()
    repo.get.return_value = job
    repo.update.side_effect = lambda j: j
    service = UpdateJobService(repo)

    service.execute(UpdateJobInput(job_id="abc1234567", enabled=True))

    updated = repo.update.call_args[0][0]
    assert updated.catalog == "retail"
    assert updated.cron is None


def test_update_bumps_updated_at():
    repo = MagicMock()
    job = _existing_job()
    repo.get.return_value = job
    repo.update.side_effect = lambda j: j
    service = UpdateJobService(repo)

    service.execute(UpdateJobInput(job_id="abc1234567", enabled=True))

    updated = repo.update.call_args[0][0]
    assert updated.updated_at > job.created_at


def test_update_raises_app_not_found():
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("ghost")
    service = UpdateJobService(repo)

    with pytest.raises(AppJobNotFoundError) as exc_info:
        service.execute(UpdateJobInput(job_id="ghost", enabled=True))
    assert exc_info.value.job_id == "ghost"
