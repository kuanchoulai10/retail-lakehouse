from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.use_cases import (
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_use_case,
    get_list_jobs_use_case,
)
from adapter.outbound.in_memory_job_run_executor import InMemoryJobRunExecutor
from adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from application.domain.service.create_job import CreateJobService
from application.domain.service.delete_job import DeleteJobService
from application.domain.service.get_job import GetJobService
from application.domain.service.list_jobs import ListJobsService


def test_get_create_job_use_case():
    repo = InMemoryJobsRepo()
    executor = InMemoryJobRunExecutor()
    result = get_create_job_use_case(repo=repo, executor=executor)
    assert isinstance(result, CreateJobService)


def test_get_create_job_use_case_injects_both_collaborators():
    repo = MagicMock()
    executor = MagicMock()
    service = get_create_job_use_case(repo=repo, executor=executor)
    assert isinstance(service, CreateJobService)
    assert service._repo is repo
    assert service._executor is executor


def test_get_delete_job_use_case():
    repo = InMemoryJobsRepo()
    result = get_delete_job_use_case(repo=repo)
    assert isinstance(result, DeleteJobService)


def test_get_get_job_use_case():
    repo = InMemoryJobsRepo()
    result = get_get_job_use_case(repo=repo)
    assert isinstance(result, GetJobService)


def test_get_list_jobs_use_case():
    repo = InMemoryJobsRepo()
    result = get_list_jobs_use_case(repo=repo)
    assert isinstance(result, ListJobsService)
