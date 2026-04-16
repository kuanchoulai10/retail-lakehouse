from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from application.domain.service.create_job import CreateJobService
from application.domain.service.delete_job import DeleteJobService
from application.domain.service.get_job import GetJobService
from application.domain.service.list_jobs import ListJobsService

from dependencies.repos import get_job_run_executor, get_jobs_repo

if TYPE_CHECKING:
    from application.port.inbound import (
        CreateJobUseCase,
        DeleteJobUseCase,
        GetJobUseCase,
        ListJobsUseCase,
    )
    from application.port.outbound.job_run_executor import JobRunExecutor
    from application.port.outbound.jobs_repo import BaseJobsRepo


def get_create_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
    executor: JobRunExecutor = Depends(get_job_run_executor),
) -> CreateJobUseCase:
    return CreateJobService(repo, executor)


def get_delete_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> DeleteJobUseCase:
    return DeleteJobService(repo)


def get_get_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> GetJobUseCase:
    return GetJobService(repo)


def get_list_jobs_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> ListJobsUseCase:
    return ListJobsService(repo)
