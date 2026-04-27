"""Provide repository and executor dependencies."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends

from adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from adapter.outbound.job_run.submit_job_run_in_memory_gateway import (
    SubmitJobRunInMemoryGateway,
)
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from adapter.outbound.job_run.k8s.submit_job_run_k8s_gateway import (
    SubmitJobRunK8sGateway,
)
from adapter.outbound.job_run.k8s.k8s_executor_config import K8sExecutorConfig
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.engine_factory import build_engine
from bootstrap.configs import (
    DatabaseBackend,
    SubmitJobRunGatewayAdapter,
    JobRunsRepoAdapter,
    JobsRepoAdapter,
)
from bootstrap.dependencies.k8s import get_k8s_api
from bootstrap.dependencies.settings import get_settings

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from application.port.outbound.job_run.submit_job_run.gateway import (
        SubmitJobRunGateway,
    )
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo
    from application.port.outbound.job.jobs_repo import JobsRepo
    from bootstrap.configs import AppSettings


@lru_cache(maxsize=1)
def _in_memory_jobs_repo_singleton() -> JobsInMemoryRepo:
    return JobsInMemoryRepo()


@lru_cache(maxsize=1)
def _in_memory_job_runs_repo_singleton() -> JobRunsInMemoryRepo:
    return JobRunsInMemoryRepo()


_engine_cache: dict[tuple[str, str], Engine] = {}


def _cached_sql_engine(settings: AppSettings) -> Engine:
    backend = settings.database_backend
    if backend == DatabaseBackend.POSTGRES:
        key = (backend.value, settings.postgres.db_url)
    elif backend == DatabaseBackend.SQLITE:
        key = (backend.value, settings.sqlite.db_path)
    else:
        raise ValueError(f"No SQL engine for backend {backend.value!r}")

    if key not in _engine_cache:
        _engine_cache[key] = build_engine(settings)
    return _engine_cache[key]


def get_jobs_repo(
    settings: AppSettings = Depends(get_settings),
) -> JobsRepo:
    """Return the Job-definition repository based on AppSettings.jobs_repo_adapter."""
    if settings.jobs_repo_adapter == JobsRepoAdapter.IN_MEMORY:
        return _in_memory_jobs_repo_singleton()
    return JobsSqlRepo(_cached_sql_engine(settings))


def get_job_runs_repo(
    settings: AppSettings = Depends(get_settings),
) -> JobRunsRepo:
    """Return the JobRun repository based on AppSettings.job_runs_repo_adapter."""
    if settings.job_runs_repo_adapter == JobRunsRepoAdapter.IN_MEMORY:
        return _in_memory_job_runs_repo_singleton()
    return JobRunsSqlRepo(_cached_sql_engine(settings))


@lru_cache(maxsize=1)
def _in_memory_executor_singleton() -> SubmitJobRunInMemoryGateway:
    return SubmitJobRunInMemoryGateway()


def get_job_run_executor(
    settings: AppSettings = Depends(get_settings),
) -> SubmitJobRunGateway:
    """Return the JobRun executor based on AppSettings.submit_job_run_gateway_adapter."""
    if settings.submit_job_run_gateway_adapter == SubmitJobRunGatewayAdapter.IN_MEMORY:
        return _in_memory_executor_singleton()
    api = get_k8s_api()
    k8s_config = K8sExecutorConfig(
        namespace=settings.k8s.namespace,
        image=settings.k8s.image,
        image_pull_policy=settings.k8s.image_pull_policy,
        spark_version=settings.k8s.spark_version,
        service_account=settings.k8s.service_account,
        iceberg_jar=settings.k8s.iceberg_jar,
        iceberg_aws_jar=settings.k8s.iceberg_aws_jar,
    )
    return SubmitJobRunK8sGateway(api, k8s_config)
