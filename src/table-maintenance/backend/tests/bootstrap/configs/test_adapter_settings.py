"""Tests for AppSettings adapter configuration."""

from bootstrap.configs import (
    AppSettings,
    DatabaseBackend,
    SubmitJobRunGatewayAdapter,
    JobRunsRepoAdapter,
    JobsRepoAdapter,
)


def test_app_settings_defaults():
    """Verify that AppSettings uses in-memory adapters and SQLite by default."""
    s = AppSettings()
    assert s.jobs_repo_adapter == JobsRepoAdapter.IN_MEMORY
    assert s.job_runs_repo_adapter == JobRunsRepoAdapter.IN_MEMORY
    assert s.submit_job_run_gateway_adapter == SubmitJobRunGatewayAdapter.IN_MEMORY
    assert s.database_backend == DatabaseBackend.SQLITE


def test_app_settings_env_override_jobs_repo_adapter(monkeypatch):
    """Verify that GLAC_JOBS_REPO_ADAPTER env var overrides jobs_repo_adapter."""
    monkeypatch.setenv("GLAC_JOBS_REPO_ADAPTER", "sql")
    s = AppSettings()
    assert s.jobs_repo_adapter == JobsRepoAdapter.SQL


def test_app_settings_env_override_job_runs_repo_adapter(monkeypatch):
    """Verify that GLAC_JOB_RUNS_REPO_ADAPTER env var overrides job_runs_repo_adapter."""
    monkeypatch.setenv("GLAC_JOB_RUNS_REPO_ADAPTER", "sql")
    s = AppSettings()
    assert s.job_runs_repo_adapter == JobRunsRepoAdapter.SQL


def test_app_settings_env_override_submit_job_run_gateway_adapter(monkeypatch):
    """Verify that GLAC_SUBMIT_JOB_RUN_GATEWAY_ADAPTER env var overrides submit_job_run_gateway_adapter."""
    monkeypatch.setenv("GLAC_SUBMIT_JOB_RUN_GATEWAY_ADAPTER", "k8s")
    s = AppSettings()
    assert s.submit_job_run_gateway_adapter == SubmitJobRunGatewayAdapter.K8S


def test_app_settings_env_override_database_backend(monkeypatch):
    """Verify that GLAC_DATABASE_BACKEND env var overrides database_backend."""
    monkeypatch.setenv("GLAC_DATABASE_BACKEND", "postgres")
    s = AppSettings()
    assert s.database_backend == DatabaseBackend.POSTGRES
