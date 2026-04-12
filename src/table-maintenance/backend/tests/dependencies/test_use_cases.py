from __future__ import annotations

from dependencies.use_cases import (
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_use_case,
    get_list_jobs_use_case,
)
from jobs.adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.domain.service.delete_job import DeleteJobService
from jobs.application.domain.service.get_job import GetJobService
from jobs.application.domain.service.list_jobs import ListJobsService


def test_get_create_job_use_case():
    repo = InMemoryJobsRepo()
    result = get_create_job_use_case(repo=repo)
    assert isinstance(result, CreateJobService)


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
