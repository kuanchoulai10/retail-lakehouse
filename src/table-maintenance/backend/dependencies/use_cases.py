from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from application.domain.service.create_job import CreateJobService
from application.domain.service.create_job_run import CreateJobRunService
from application.domain.service.delete_job import DeleteJobService
from application.domain.service.get_job import GetJobService
from application.domain.service.get_job_run import GetJobRunService
from application.domain.service.list_job_runs import ListJobRunsService
from application.domain.service.list_jobs import ListJobsService
from application.domain.service.update_job import UpdateJobService

from dependencies.repos import (
    get_job_run_executor,
    get_job_runs_repo,
    get_jobs_repo,
)

if TYPE_CHECKING:
    from application.port.inbound import (
        CreateJobRunUseCase,
        CreateJobUseCase,
        DeleteJobUseCase,
        GetJobRunUseCase,
        GetJobUseCase,
        ListJobRunsUseCase,
        ListJobsUseCase,
        UpdateJobUseCase,
    )
    from application.port.outbound.job_run_executor import JobRunExecutor
    from application.port.outbound.job_runs_repo import BaseJobRunsRepo
    from application.port.outbound.jobs_repo import BaseJobsRepo


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


def get_update_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> UpdateJobUseCase:
    return UpdateJobService(repo)


def get_create_job_run_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
    executor: JobRunExecutor = Depends(get_job_run_executor),
) -> CreateJobRunUseCase:
    return CreateJobRunService(repo, executor)


def get_list_job_runs_use_case(
    repo: BaseJobRunsRepo = Depends(get_job_runs_repo),
) -> ListJobRunsUseCase:
    return ListJobRunsService(repo)


def get_get_job_run_use_case(
    repo: BaseJobRunsRepo = Depends(get_job_runs_repo),
) -> GetJobRunUseCase:
    return GetJobRunService(repo)
