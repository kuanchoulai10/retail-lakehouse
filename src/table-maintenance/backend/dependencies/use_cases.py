from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.domain.service.delete_job import DeleteJobService
from jobs.application.domain.service.get_job import GetJobService
from jobs.application.domain.service.list_jobs import ListJobsService

from dependencies.repos import get_jobs_repo

if TYPE_CHECKING:
    from jobs.application.port.inbound import (
        CreateJobUseCase,
        DeleteJobUseCase,
        GetJobUseCase,
        ListJobsUseCase,
    )
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo


def get_create_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> CreateJobUseCase:
    return CreateJobService(repo)


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
