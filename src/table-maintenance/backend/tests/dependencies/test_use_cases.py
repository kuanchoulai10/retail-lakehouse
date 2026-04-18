from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.use_cases import (
    get_create_job_run_use_case,
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_run_use_case,
    get_get_job_use_case,
    get_list_job_runs_use_case,
    get_list_jobs_use_case,
    get_update_job_use_case,
)
from adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from adapter.outbound.job_run.job_run_in_memory_executor import JobRunInMemoryExecutor
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from application.domain.service.job.create_job import CreateJobService
from application.domain.service.job.delete_job import DeleteJobService
from application.domain.service.job.get_job import GetJobService
from application.domain.service.job.list_jobs import ListJobsService
from application.domain.service.job.update_job import UpdateJobService
from application.domain.service.job_run.create_job_run import CreateJobRunService
from application.domain.service.job_run.get_job_run import GetJobRunService
from application.domain.service.job_run.list_job_runs import ListJobRunsService


def test_get_create_job_use_case():
    repo = JobsInMemoryRepo()
    result = get_create_job_use_case(repo=repo)
    assert isinstance(result, CreateJobService)


def test_get_delete_job_use_case():
    repo = JobsInMemoryRepo()
    result = get_delete_job_use_case(repo=repo)
    assert isinstance(result, DeleteJobService)


def test_get_get_job_use_case():
    repo = JobsInMemoryRepo()
    result = get_get_job_use_case(repo=repo)
    assert isinstance(result, GetJobService)


def test_get_list_jobs_use_case():
    repo = JobsInMemoryRepo()
    result = get_list_jobs_use_case(repo=repo)
    assert isinstance(result, ListJobsService)


def test_get_update_job_use_case():
    repo = JobsInMemoryRepo()
    result = get_update_job_use_case(repo=repo)
    assert isinstance(result, UpdateJobService)


def test_get_create_job_run_use_case():
    repo = JobsInMemoryRepo()
    executor = JobRunInMemoryExecutor()
    result = get_create_job_run_use_case(repo=repo, executor=executor)
    assert isinstance(result, CreateJobRunService)


def test_get_create_job_run_use_case_injects_collaborators():
    repo = MagicMock()
    executor = MagicMock()
    service = get_create_job_run_use_case(repo=repo, executor=executor)
    assert isinstance(service, CreateJobRunService)
    assert service._repo is repo
    assert service._executor is executor


def test_get_list_job_runs_use_case():
    repo = JobRunsInMemoryRepo()
    result = get_list_job_runs_use_case(repo=repo)
    assert isinstance(result, ListJobRunsService)


def test_get_get_job_run_use_case():
    repo = JobRunsInMemoryRepo()
    result = get_get_job_run_use_case(repo=repo)
    assert isinstance(result, GetJobRunService)
