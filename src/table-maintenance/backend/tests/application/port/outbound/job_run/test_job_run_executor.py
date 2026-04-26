"""Tests for JobRunExecutor."""

from abc import ABC

from application.port.outbound.job_run.job_run_executor import JobRunExecutor


def test_is_abstract():
    """Verify that JobRunExecutor is an abstract base class."""
    assert issubclass(JobRunExecutor, ABC)


def test_has_submit_method():
    """Verify that JobRunExecutor declares submit as an abstract method."""
    assert "submit" in JobRunExecutor.__abstractmethods__
