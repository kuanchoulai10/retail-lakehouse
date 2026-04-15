from adapter.outbound.k8s.status_mapper import status_from_k8s
from application.domain import JobStatus


def test_status_empty_state_is_pending():
    assert status_from_k8s("SparkApplication", "") == JobStatus.PENDING


def test_status_running():
    assert status_from_k8s("SparkApplication", "RUNNING") == JobStatus.RUNNING


def test_status_completed():
    assert status_from_k8s("SparkApplication", "COMPLETED") == JobStatus.COMPLETED


def test_status_failed_states():
    for state in ("FAILED", "SUBMISSION_FAILED", "INVALIDATING"):
        assert status_from_k8s("SparkApplication", state) == JobStatus.FAILED


def test_status_unknown_state():
    assert status_from_k8s("SparkApplication", "WEIRD_STATE") == JobStatus.UNKNOWN


def test_scheduled_app_always_running():
    assert status_from_k8s("ScheduledSparkApplication", "") == JobStatus.RUNNING
