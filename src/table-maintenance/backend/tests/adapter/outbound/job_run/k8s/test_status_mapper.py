"""Tests for status_from_k8s."""

from core.adapter.outbound.job_run.k8s.status_mapper import status_from_k8s
from application.domain.model.job_run import JobRunStatus


def test_status_empty_state_is_pending():
    """Verify that an empty state maps to PENDING status."""
    assert status_from_k8s("SparkApplication", "") == JobRunStatus.PENDING


def test_status_running():
    """Verify that RUNNING state maps to RUNNING status."""
    assert status_from_k8s("SparkApplication", "RUNNING") == JobRunStatus.RUNNING


def test_status_completed():
    """Verify that COMPLETED state maps to COMPLETED status."""
    assert status_from_k8s("SparkApplication", "COMPLETED") == JobRunStatus.COMPLETED


def test_status_failed_states():
    """Verify that failure states map to FAILED status."""
    for state in ("FAILED", "SUBMISSION_FAILED", "INVALIDATING"):
        assert status_from_k8s("SparkApplication", state) == JobRunStatus.FAILED


def test_status_unknown_state_maps_to_failed():
    """Verify that an unrecognized state maps to FAILED status."""
    assert status_from_k8s("SparkApplication", "WEIRD_STATE") == JobRunStatus.FAILED


def test_scheduled_app_always_running():
    """Verify that ScheduledSparkApplication always maps to RUNNING."""
    assert status_from_k8s("ScheduledSparkApplication", "") == JobRunStatus.RUNNING


def test_return_type_is_job_run_status():
    """Verify that the return type is JobRunStatus."""
    result = status_from_k8s("SparkApplication", "RUNNING")
    assert isinstance(result, JobRunStatus)
