from datetime import UTC, datetime

from configs import JobType
from models import JobResponse, JobStatus, status_from_k8s


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


def test_job_response_fields():
    r = JobResponse(
        name="table-maintenance-rewrite-data-files-abc123",
        kind="SparkApplication",
        namespace="default",
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=datetime(2026, 4, 4, tzinfo=UTC),
    )
    assert r.name == "table-maintenance-rewrite-data-files-abc123"
    assert r.status == JobStatus.COMPLETED
