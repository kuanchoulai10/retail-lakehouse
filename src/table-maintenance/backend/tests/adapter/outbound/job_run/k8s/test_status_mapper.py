from adapter.outbound.job_run.k8s.status_mapper import status_from_k8s
from application.domain.model.job_run import JobRunStatus


def test_status_empty_state_is_pending():
    assert status_from_k8s("SparkApplication", "") == JobRunStatus.PENDING


def test_status_running():
    assert status_from_k8s("SparkApplication", "RUNNING") == JobRunStatus.RUNNING


def test_status_completed():
    assert status_from_k8s("SparkApplication", "COMPLETED") == JobRunStatus.COMPLETED


def test_status_failed_states():
    for state in ("FAILED", "SUBMISSION_FAILED", "INVALIDATING"):
        assert status_from_k8s("SparkApplication", state) == JobRunStatus.FAILED


def test_status_unknown_state():
    assert status_from_k8s("SparkApplication", "WEIRD_STATE") == JobRunStatus.UNKNOWN


def test_scheduled_app_always_running():
    assert status_from_k8s("ScheduledSparkApplication", "") == JobRunStatus.RUNNING


def test_return_type_is_job_run_status():
    result = status_from_k8s("SparkApplication", "RUNNING")
    assert isinstance(result, JobRunStatus)
