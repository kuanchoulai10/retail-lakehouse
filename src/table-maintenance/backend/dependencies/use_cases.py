"""Provide use case dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from application.domain.service.job.create_job import CreateJobService
from application.domain.service.job.delete_job import DeleteJobService
from application.domain.service.job.get_job import GetJobService
from application.domain.service.job.list_jobs import ListJobsService
from application.domain.service.job.update_job import UpdateJobService
from application.domain.service.job_run.create_job_run import CreateJobRunService
from application.domain.service.job_run.get_job_run import GetJobRunService
from application.domain.service.job_run.list_job_runs import ListJobRunsService

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
    from application.port.outbound.job_run.job_run_executor import JobRunExecutor
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo
    from application.port.outbound.job.jobs_repo import JobsRepo


def get_create_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> CreateJobUseCase:
    """Provide the CreateJob use case with injected dependencies."""
    return CreateJobService(repo)


def get_delete_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> DeleteJobUseCase:
    """Provide the DeleteJob use case with injected dependencies."""
    return DeleteJobService(repo)


def get_get_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> GetJobUseCase:
    """Provide the GetJob use case with injected dependencies."""
    return GetJobService(repo)


def get_list_jobs_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> ListJobsUseCase:
    """Provide the ListJobs use case with injected dependencies."""
    return ListJobsService(repo)


def get_update_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> UpdateJobUseCase:
    """Provide the UpdateJob use case with injected dependencies."""
    return UpdateJobService(repo)


def get_create_job_run_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    executor: JobRunExecutor = Depends(get_job_run_executor),
) -> CreateJobRunUseCase:
    """Provide the CreateJobRun use case with injected dependencies."""
    return CreateJobRunService(repo, executor)


def get_list_job_runs_use_case(
    repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> ListJobRunsUseCase:
    """Provide the ListJobRuns use case with injected dependencies."""
    return ListJobRunsService(repo)


def get_get_job_run_use_case(
    repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> GetJobRunUseCase:
    """Provide the GetJobRun use case with injected dependencies."""
    return GetJobRunService(repo)
