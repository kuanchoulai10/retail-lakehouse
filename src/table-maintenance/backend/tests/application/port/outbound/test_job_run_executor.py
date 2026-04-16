from abc import ABC

from application.port.outbound.job_run_executor import JobRunExecutor


def test_is_abstract():
    assert issubclass(JobRunExecutor, ABC)


def test_has_trigger_method():
    assert "trigger" in JobRunExecutor.__abstractmethods__
