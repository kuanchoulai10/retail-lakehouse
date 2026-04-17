from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends

from adapter.outbound.job.in_memory_jobs_repo import InMemoryJobsRepo
from adapter.outbound.job.sql.sql_jobs_repo import SqlJobsRepo
from adapter.outbound.job_run.k8s.k8s_job_run_executor import K8sJobRunExecutor
from adapter.outbound.job_run.k8s.k8s_job_runs_repo import K8sJobRunsRepo
from adapter.outbound.sql.engine_factory import build_engine
from configs import JobsRepoBackend
from dependencies.k8s import get_k8s_api
from dependencies.settings import get_settings

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi
    from sqlalchemy import Engine

    from application.port.outbound.job_run.job_run_executor import JobRunExecutor
    from application.port.outbound.job_run.job_runs_repo import BaseJobRunsRepo
    from application.port.outbound.job.jobs_repo import BaseJobsRepo
    from configs import AppSettings


@lru_cache(maxsize=1)
def _in_memory_jobs_repo_singleton() -> InMemoryJobsRepo:
    return InMemoryJobsRepo()


_engine_cache: dict[tuple[str, str], Engine] = {}


def _cached_sql_engine(settings: AppSettings) -> Engine:
    backend = settings.jobs_repo_backend
    if backend == JobsRepoBackend.POSTGRES:
        key = (backend.value, settings.postgres.db_url)
    elif backend == JobsRepoBackend.SQLITE:
        key = (backend.value, settings.sqlite.db_path)
    else:
        raise ValueError(f"No SQL engine for backend {backend.value!r}")

    if key not in _engine_cache:
        _engine_cache[key] = build_engine(backend, settings)
    return _engine_cache[key]


def get_jobs_repo(
    settings: AppSettings = Depends(get_settings),
) -> BaseJobsRepo:
    """Return the Job-definition repository based on AppSettings.jobs_repo_backend."""
    if settings.jobs_repo_backend == JobsRepoBackend.IN_MEMORY:
        return _in_memory_jobs_repo_singleton()
    return SqlJobsRepo(_cached_sql_engine(settings))


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
