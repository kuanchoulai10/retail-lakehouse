"""Tests for use case dependency providers."""

from __future__ import annotations

from unittest.mock import MagicMock

from api.dependencies.use_cases import (
    get_create_job_run_use_case,
    get_create_job_use_case,
    get_event_dispatcher,
    get_get_job_run_use_case,
    get_get_job_use_case,
    get_list_job_runs_use_case,
    get_list_jobs_use_case,
    get_triggered_handler,
    get_update_job_use_case,
)
from core.adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from core.adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from core.application.event_handler.event_dispatcher import EventDispatcher
from core.application.event_handler.job_triggered_handler import JobTriggeredHandler
from core.application.service.job.create_job import CreateJobService
from core.application.service.job.get_job import GetJobService
from core.application.service.job.list_jobs import ListJobsService
from core.application.service.job.update_job import UpdateJobService
from core.application.service.job_run.create_job_run import CreateJobRunService
from core.application.service.job_run.get_job_run import GetJobRunService
from core.application.service.job_run.list_job_runs import ListJobRunsService


def test_get_create_job_use_case():
    """Verify that get_create_job_use_case returns a CreateJobService."""
    repo = JobsInMemoryRepo()
    dispatcher = EventDispatcher()
    result = get_create_job_use_case(repo=repo, dispatcher=dispatcher)
    assert isinstance(result, CreateJobService)


def test_get_get_job_use_case():
    """Verify that get_get_job_use_case returns a GetJobService."""
    repo = JobsInMemoryRepo()
    result = get_get_job_use_case(repo=repo)
    assert isinstance(result, GetJobService)


def test_get_list_jobs_use_case():
    """Verify that get_list_jobs_use_case returns a ListJobsService."""
    repo = JobsInMemoryRepo()
    result = get_list_jobs_use_case(repo=repo)
    assert isinstance(result, ListJobsService)


def test_get_update_job_use_case():
    """Verify that get_update_job_use_case returns an UpdateJobService."""
    repo = JobsInMemoryRepo()
    dispatcher = EventDispatcher()
    result = get_update_job_use_case(repo=repo, dispatcher=dispatcher)
    assert isinstance(result, UpdateJobService)


def test_get_create_job_run_use_case():
    """Verify that get_create_job_run_use_case returns a CreateJobRunService."""
    repo = JobsInMemoryRepo()
    job_runs_repo = JobRunsInMemoryRepo()
    handler = get_triggered_handler(job_runs_repo=job_runs_repo)
    dispatcher = get_event_dispatcher(triggered_handler=handler)
    result = get_create_job_run_use_case(
        repo=repo,
        job_runs_repo=job_runs_repo,
        dispatcher=dispatcher,
        triggered_handler=handler,
    )
    assert isinstance(result, CreateJobRunService)


def test_get_create_job_run_use_case_injects_collaborators():
    """Verify that get_create_job_run_use_case injects repo and job_runs_repo into service."""
    repo = MagicMock()
    job_runs_repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo)
    dispatcher = EventDispatcher()
    service = get_create_job_run_use_case(
        repo=repo,
        job_runs_repo=job_runs_repo,
        dispatcher=dispatcher,
        triggered_handler=handler,
    )
    assert isinstance(service, CreateJobRunService)
    assert service._repo is repo
    assert service._job_runs_repo is job_runs_repo


def test_get_list_job_runs_use_case():
    """Verify that get_list_job_runs_use_case returns a ListJobRunsService."""
    repo = JobRunsInMemoryRepo()
    result = get_list_job_runs_use_case(repo=repo)
    assert isinstance(result, ListJobRunsService)


def test_get_get_job_run_use_case():
    """Verify that get_get_job_run_use_case returns a GetJobRunService."""
    repo = JobRunsInMemoryRepo()
    result = get_get_job_run_use_case(repo=repo)
    assert isinstance(result, GetJobRunService)
