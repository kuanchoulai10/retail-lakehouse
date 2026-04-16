from abc import ABC

from application.port.outbound.job_runs_repo import BaseJobRunsRepo


def test_is_abstract():
    assert issubclass(BaseJobRunsRepo, ABC)


def test_has_required_abstract_methods():
    methods = BaseJobRunsRepo.__abstractmethods__
    assert "get" in methods
    assert "list_for_job" in methods
    assert "list_all" in methods
