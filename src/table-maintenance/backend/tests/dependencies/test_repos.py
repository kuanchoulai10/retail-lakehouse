"""Tests for repository and executor dependency providers."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from core.adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from core.adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from core.adapter.outbound.job_run.job_run_in_memory_executor import (
    JobRunInMemoryExecutor,
)
from core.adapter.outbound.job_run.k8s.job_run_k8s_executor import JobRunK8sExecutor
from core.adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from core.configs import (
    AppSettings,
    DatabaseBackend,
    JobRunExecutorAdapter,
    JobRunsRepoAdapter,
    JobsRepoAdapter,
)
from api.dependencies.repos import (
    _engine_cache,
    _in_memory_executor_singleton,
    _in_memory_jobs_repo_singleton,
    _in_memory_job_runs_repo_singleton,
    get_job_run_executor,
    get_job_runs_repo,
    get_jobs_repo,
)


def _clear_caches() -> None:
    """Clear all singleton and engine caches between tests."""
    _in_memory_jobs_repo_singleton.cache_clear()
    _in_memory_job_runs_repo_singleton.cache_clear()
    _in_memory_executor_singleton.cache_clear()
    _engine_cache.clear()


def test_get_jobs_repo_returns_in_memory_by_default():
    """Verify that get_jobs_repo returns JobsInMemoryRepo with default settings."""
    _clear_caches()
    settings = AppSettings()
    result = get_jobs_repo(settings=settings)
    assert isinstance(result, JobsInMemoryRepo)


def test_in_memory_backend_is_module_singleton():
    """Verify that in-memory jobs repo is returned as a singleton."""
    _clear_caches()
    settings = AppSettings()
    first = get_jobs_repo(settings=settings)
    second = get_jobs_repo(settings=settings)
    assert first is second


def test_get_jobs_repo_returns_sql_for_sqlite():
    """Verify that get_jobs_repo returns JobsSqlRepo when configured for SQLite."""
    _clear_caches()
    settings = AppSettings()
    settings.jobs_repo_adapter = JobsRepoAdapter.SQL
    settings.database_backend = DatabaseBackend.SQLITE
    settings.sqlite.db_path = ":memory:"
    result = get_jobs_repo(settings=settings)
    assert isinstance(result, JobsSqlRepo)


def test_get_jobs_repo_returns_sql_for_postgres(monkeypatch):
    """Verify that get_jobs_repo returns JobsSqlRepo when configured for Postgres."""
    _clear_caches()
    from core.adapter.outbound.sql import engine_factory as ef

    fake_engine = MagicMock(name="engine")
    monkeypatch.setattr(ef, "create_engine", MagicMock(return_value=fake_engine))

    settings = AppSettings()
    settings.jobs_repo_adapter = JobsRepoAdapter.SQL
    settings.database_backend = DatabaseBackend.POSTGRES
    settings.postgres.db_url = "postgresql+psycopg://u:p@h/db"
    result = get_jobs_repo(settings=settings)
    assert isinstance(result, JobsSqlRepo)


def test_sql_engine_cached_per_backend_and_url():
    """Verify that the SQL engine is cached and reused across repo instances."""
    _clear_caches()
    settings = AppSettings()
    settings.jobs_repo_adapter = JobsRepoAdapter.SQL
    settings.database_backend = DatabaseBackend.SQLITE
    settings.sqlite.db_path = ":memory:"
    first = get_jobs_repo(settings=settings)
    second = get_jobs_repo(settings=settings)
    assert isinstance(first, JobsSqlRepo)
    assert isinstance(second, JobsSqlRepo)
    assert first._engine is second._engine


def test_get_job_runs_repo_returns_in_memory_by_default():
    """Verify that get_job_runs_repo returns JobRunsInMemoryRepo with default settings."""
    _clear_caches()
    settings = AppSettings()
    result = get_job_runs_repo(settings=settings)
    assert isinstance(result, JobRunsInMemoryRepo)


def test_get_job_runs_repo_returns_sql_for_sqlite():
    """Verify that get_job_runs_repo returns JobRunsSqlRepo when configured for SQLite."""
    _clear_caches()
    settings = AppSettings()
    settings.job_runs_repo_adapter = JobRunsRepoAdapter.SQL
    settings.database_backend = DatabaseBackend.SQLITE
    settings.sqlite.db_path = ":memory:"
    result = get_job_runs_repo(settings=settings)
    assert isinstance(result, JobRunsSqlRepo)


def test_get_job_run_executor_returns_in_memory_by_default():
    """Verify that get_job_run_executor returns JobRunInMemoryExecutor with default settings."""
    _clear_caches()
    _in_memory_executor_singleton.cache_clear()
    settings = AppSettings()
    result = get_job_run_executor(settings=settings)
    assert isinstance(result, JobRunInMemoryExecutor)


def test_get_job_run_executor_returns_k8s_when_configured(monkeypatch):
    """Verify that get_job_run_executor returns JobRunK8sExecutor when configured for K8s."""
    _clear_caches()
    from api.dependencies import repos as repos_mod

    monkeypatch.setattr(repos_mod, "get_k8s_api", MagicMock())

    settings = AppSettings()
    settings.job_run_executor_adapter = JobRunExecutorAdapter.K8S
    result = get_job_run_executor(settings=settings)
    assert isinstance(result, JobRunK8sExecutor)
