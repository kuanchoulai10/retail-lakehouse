"""Tests for JobRunExecutor."""

from abc import ABC

from application.port.outbound.job_run.job_run_executor import JobRunExecutor


def test_is_abstract():
    """Verify that JobRunExecutor is an abstract base class."""
    assert issubclass(JobRunExecutor, ABC)


def test_has_trigger_method():
    """Verify that JobRunExecutor declares trigger as an abstract method."""
    assert "trigger" in JobRunExecutor.__abstractmethods__
