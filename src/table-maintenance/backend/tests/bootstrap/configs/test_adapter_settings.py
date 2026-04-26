"""Tests for AppSettings adapter configuration."""

from bootstrap.configs import (
    AppSettings,
    DatabaseBackend,
    JobRunExecutorAdapter,
    JobRunsRepoAdapter,
    JobsRepoAdapter,
)


def test_app_settings_defaults():
    """Verify that AppSettings uses in-memory adapters and SQLite by default."""
    s = AppSettings()
    assert s.jobs_repo_adapter == JobsRepoAdapter.IN_MEMORY
    assert s.job_runs_repo_adapter == JobRunsRepoAdapter.IN_MEMORY
    assert s.job_run_executor_adapter == JobRunExecutorAdapter.IN_MEMORY
    assert s.database_backend == DatabaseBackend.SQLITE


def test_app_settings_env_override_jobs_repo_adapter(monkeypatch):
    """Verify that BACKEND_JOBS_REPO_ADAPTER env var overrides jobs_repo_adapter."""
    monkeypatch.setenv("GLAC_JOBS_REPO_ADAPTER", "sql")
    s = AppSettings()
    assert s.jobs_repo_adapter == JobsRepoAdapter.SQL


def test_app_settings_env_override_job_runs_repo_adapter(monkeypatch):
    """Verify that BACKEND_JOB_RUNS_REPO_ADAPTER env var overrides job_runs_repo_adapter."""
    monkeypatch.setenv("GLAC_JOB_RUNS_REPO_ADAPTER", "sql")
    s = AppSettings()
    assert s.job_runs_repo_adapter == JobRunsRepoAdapter.SQL


def test_app_settings_env_override_job_run_executor_adapter(monkeypatch):
    """Verify that BACKEND_JOB_RUN_EXECUTOR_ADAPTER env var overrides job_run_executor_adapter."""
    monkeypatch.setenv("GLAC_JOB_RUN_EXECUTOR_ADAPTER", "k8s")
    s = AppSettings()
    assert s.job_run_executor_adapter == JobRunExecutorAdapter.K8S


def test_app_settings_env_override_database_backend(monkeypatch):
    """Verify that BACKEND_DATABASE_BACKEND env var overrides database_backend."""
    monkeypatch.setenv("GLAC_DATABASE_BACKEND", "postgres")
    s = AppSettings()
    assert s.database_backend == DatabaseBackend.POSTGRES
