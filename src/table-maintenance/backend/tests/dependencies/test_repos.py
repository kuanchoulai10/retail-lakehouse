from __future__ import annotations

from unittest.mock import MagicMock

from adapter.outbound.job.in_memory_jobs_repo import InMemoryJobsRepo
from adapter.outbound.job.sql.sql_jobs_repo import SqlJobsRepo
from adapter.outbound.job_run.k8s.k8s_job_run_executor import K8sJobRunExecutor
from adapter.outbound.job_run.k8s.k8s_job_runs_repo import K8sJobRunsRepo
from configs import AppSettings, JobsRepoBackend
from dependencies.repos import (
    _engine_cache,
    _in_memory_jobs_repo_singleton,
    get_job_run_executor,
    get_job_runs_repo,
    get_jobs_repo,
)


def _clear_caches() -> None:
    _in_memory_jobs_repo_singleton.cache_clear()
    _engine_cache.clear()


def test_get_jobs_repo_returns_in_memory_by_default():
    _clear_caches()
    settings = AppSettings()  # default: IN_MEMORY
    result = get_jobs_repo(settings=settings)
    assert isinstance(result, InMemoryJobsRepo)


def test_in_memory_backend_is_module_singleton():
    _clear_caches()
    settings = AppSettings()
    first = get_jobs_repo(settings=settings)
    second = get_jobs_repo(settings=settings)
    assert first is second


def test_get_jobs_repo_returns_sql_for_sqlite_backend():
    _clear_caches()
    settings = AppSettings()
    settings.jobs_repo_backend = JobsRepoBackend.SQLITE
    settings.sqlite.db_path = ":memory:"
    result = get_jobs_repo(settings=settings)
    assert isinstance(result, SqlJobsRepo)


def test_get_jobs_repo_returns_sql_for_postgres_backend(monkeypatch):
    _clear_caches()
    from adapter.outbound.sql import engine_factory as ef

    fake_engine = MagicMock(name="engine")
    monkeypatch.setattr(ef, "create_engine", MagicMock(return_value=fake_engine))

    settings = AppSettings()
    settings.jobs_repo_backend = JobsRepoBackend.POSTGRES
    settings.postgres.db_url = "postgresql+psycopg://u:p@h/db"
    result = get_jobs_repo(settings=settings)
    assert isinstance(result, SqlJobsRepo)


def test_sql_engine_cached_per_backend_and_url():
    _clear_caches()
    settings = AppSettings()
    settings.jobs_repo_backend = JobsRepoBackend.SQLITE
    settings.sqlite.db_path = ":memory:"
    first = get_jobs_repo(settings=settings)
    second = get_jobs_repo(settings=settings)
    assert isinstance(first, SqlJobsRepo)
    assert isinstance(second, SqlJobsRepo)
    assert first._engine is second._engine


def test_get_job_runs_repo_returns_k8s_impl():
    api = MagicMock()
    settings = AppSettings()
    result = get_job_runs_repo(api=api, settings=settings)
    assert isinstance(result, K8sJobRunsRepo)


def test_get_job_run_executor_returns_k8s_impl():
    api = MagicMock()
    settings = AppSettings()
    result = get_job_run_executor(api=api, settings=settings)
    assert isinstance(result, K8sJobRunExecutor)
