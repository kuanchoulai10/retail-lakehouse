"""Tests for JobRunsRepo."""

from abc import ABC

from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


def test_is_abstract():
    """Verify that JobRunsRepo is an abstract base class."""
    assert issubclass(JobRunsRepo, ABC)


def test_has_required_abstract_methods():
    """Verify that JobRunsRepo declares create, get, list_for_job, and list_all as abstract."""
    methods = JobRunsRepo.__abstractmethods__
    assert "create" in methods
    assert "get" in methods
    assert "list_for_job" in methods
    assert "list_all" in methods


def test_has_count_active_for_job():
    """Verify that JobRunsRepo declares count_active_for_job as abstract."""
    assert "count_active_for_job" in JobRunsRepo.__abstractmethods__
