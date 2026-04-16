from __future__ import annotations

from unittest.mock import MagicMock

from adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from adapter.outbound.k8s.k8s_job_run_executor import K8sJobRunExecutor
from adapter.outbound.k8s.k8s_job_runs_repo import K8sJobRunsRepo
from configs import AppSettings
from dependencies.repos import (
    _in_memory_jobs_repo_singleton,
    get_job_run_executor,
    get_job_runs_repo,
    get_jobs_repo,
)


def test_get_jobs_repo_returns_in_memory_during_transition():
    result = get_jobs_repo()
    assert isinstance(result, InMemoryJobsRepo)


def test_get_jobs_repo_is_module_singleton():
    _in_memory_jobs_repo_singleton.cache_clear()
    first = get_jobs_repo()
    second = get_jobs_repo()
    assert first is second


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
