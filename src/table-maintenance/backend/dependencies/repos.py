from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends

from adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from adapter.outbound.k8s.k8s_job_run_executor import K8sJobRunExecutor
from adapter.outbound.k8s.k8s_job_runs_repo import K8sJobRunsRepo
from dependencies.k8s import get_k8s_api
from dependencies.settings import get_settings

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi

    from application.port.outbound.job_run_executor import JobRunExecutor
    from application.port.outbound.job_runs_repo import BaseJobRunsRepo
    from application.port.outbound.jobs_repo import BaseJobsRepo
    from configs import AppSettings


@lru_cache(maxsize=1)
def _in_memory_jobs_repo_singleton() -> InMemoryJobsRepo:
    return InMemoryJobsRepo()


def get_jobs_repo() -> BaseJobsRepo:
    """Return the Job-definition repository.

    Transitional: backed by InMemoryJobsRepo until the SQL repo lands (Stage 5+).
    Definitions do not persist across restarts during this window.
    """
    return _in_memory_jobs_repo_singleton()


def get_job_runs_repo(
    api: CustomObjectsApi = Depends(get_k8s_api),
    settings: AppSettings = Depends(get_settings),
) -> BaseJobRunsRepo:
    return K8sJobRunsRepo(api, settings)


def get_job_run_executor(
    api: CustomObjectsApi = Depends(get_k8s_api),
    settings: AppSettings = Depends(get_settings),
) -> JobRunExecutor:
    return K8sJobRunExecutor(api, settings)
