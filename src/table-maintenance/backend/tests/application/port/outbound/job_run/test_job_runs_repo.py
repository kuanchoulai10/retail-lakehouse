from abc import ABC

from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


def test_is_abstract():
    assert issubclass(JobRunsRepo, ABC)


def test_has_required_abstract_methods():
    methods = JobRunsRepo.__abstractmethods__
    assert "create" in methods
    assert "get" in methods
    assert "list_for_job" in methods
    assert "list_all" in methods
