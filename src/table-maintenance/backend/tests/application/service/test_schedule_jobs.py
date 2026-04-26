"""Tests for ScheduleJobsService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from core.application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
)
from core.application.port.inbound.scheduling.schedule_jobs import (
    ScheduleJobsUseCase,
)
from core.application.service.scheduling.schedule_jobs import ScheduleJobsService

NOW = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)


def _make_job(
    job_id: str = "j1",
    cron: str = "0 * * * *",
    next_run_at: datetime | None = None,
    max_active_runs: int = 1,
) -> Job:
    """Provide a schedulable Job entity."""
    return Job(
        id=JobId(job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=NOW,
        updated_at=NOW,
        cron=CronExpression(expression=cron),
        status=JobStatus.ACTIVE,
        next_run_at=next_run_at or datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
        max_active_runs=max_active_runs,
    )


def _make_service():
    """Provide a ScheduleJobsService with mocked collaborators."""
    jobs_repo = MagicMock()
    job_runs_repo = MagicMock()
    clock = MagicMock(return_value=NOW)
    outbox_repo = MagicMock()
    serializer = MagicMock()
    serializer.to_outbox_entries.return_value = []
    service = ScheduleJobsService(
        jobs_repo, job_runs_repo, clock, outbox_repo, serializer
    )
    return service, jobs_repo, job_runs_repo, outbox_repo


def test_service_implements_use_case():
    """Verify that ScheduleJobsService implements ScheduleJobsUseCase."""
    service, *_ = _make_service()
    assert isinstance(service, ScheduleJobsUseCase)


def test_no_schedulable_jobs_returns_zero():
    """Verify that execute returns zero when no jobs are due."""
    service, jobs_repo, _, _ = _make_service()
    jobs_repo.list_schedulable.return_value = []
    result = service.execute(None)
    assert result.triggered_count == 0
    assert result.job_ids == []


def test_triggers_run_for_schedulable_job():
    """Verify that execute writes outbox entries for a schedulable job."""
    service, jobs_repo, job_runs_repo, outbox_repo = _make_service()
    job = _make_job("j1")
    jobs_repo.list_schedulable.return_value = [job]
    job_runs_repo.count_active_for_job.return_value = 0

    result = service.execute(None)

    assert result.triggered_count == 1
    assert "j1" in result.job_ids
    outbox_repo.save.assert_called_once()
    jobs_repo.save_next_run_at.assert_called_once()


def test_skips_job_at_max_active_runs():
    """Verify that execute skips a job that has reached max_active_runs."""
    service, jobs_repo, job_runs_repo, outbox_repo = _make_service()
    job = _make_job("j1", max_active_runs=1)
    jobs_repo.list_schedulable.return_value = [job]
    job_runs_repo.count_active_for_job.return_value = 1

    result = service.execute(None)

    assert result.triggered_count == 0
    outbox_repo.save.assert_not_called()


def test_triggers_multiple_jobs():
    """Verify that execute triggers multiple schedulable jobs."""
    service, jobs_repo, job_runs_repo, _ = _make_service()
    jobs_repo.list_schedulable.return_value = [_make_job("j1"), _make_job("j2")]
    job_runs_repo.count_active_for_job.return_value = 0

    result = service.execute(None)

    assert result.triggered_count == 2
    assert set(result.job_ids) == {"j1", "j2"}


def test_advances_next_run_at_using_cron():
    """Verify that execute advances next_run_at to the next cron occurrence."""
    service, jobs_repo, job_runs_repo, _ = _make_service()
    job = _make_job("j1", cron="0 * * * *")
    jobs_repo.list_schedulable.return_value = [job]
    job_runs_repo.count_active_for_job.return_value = 0

    service.execute(None)

    save_call = jobs_repo.save_next_run_at.call_args
    next_time = save_call[0][1]
    assert next_time == datetime(2026, 4, 22, 11, 0, tzinfo=UTC)


def test_continues_on_single_job_failure():
    """Verify that a failure on one job does not block others."""
    service, jobs_repo, job_runs_repo, outbox_repo = _make_service()
    jobs_repo.list_schedulable.return_value = [_make_job("j1"), _make_job("j2")]
    job_runs_repo.count_active_for_job.return_value = 0
    outbox_repo.save.side_effect = [RuntimeError("boom"), None]

    result = service.execute(None)

    assert result.triggered_count == 1
    assert "j2" in result.job_ids
