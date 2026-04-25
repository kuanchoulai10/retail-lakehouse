"""Tests for JobRunStatus."""

import pytest

from core.application.domain.model.job_run import JobRunStatus


def test_enum_values():
    """Verify that all JobRunStatus members have the expected string values."""
    assert JobRunStatus.PENDING == "pending"
    assert JobRunStatus.RUNNING == "running"
    assert JobRunStatus.COMPLETED == "completed"
    assert JobRunStatus.FAILED == "failed"
    assert JobRunStatus.CANCELLED == "cancelled"


def test_pending_can_transition_to_running():
    """Verify PENDING allows transition to RUNNING."""
    assert JobRunStatus.PENDING.can_transition_to(JobRunStatus.RUNNING) is True


def test_pending_can_transition_to_failed():
    """Verify PENDING allows transition to FAILED."""
    assert JobRunStatus.PENDING.can_transition_to(JobRunStatus.FAILED) is True


def test_pending_can_transition_to_cancelled():
    """Verify PENDING allows transition to CANCELLED."""
    assert JobRunStatus.PENDING.can_transition_to(JobRunStatus.CANCELLED) is True


def test_pending_cannot_transition_to_completed():
    """Verify PENDING does not allow transition to COMPLETED."""
    assert JobRunStatus.PENDING.can_transition_to(JobRunStatus.COMPLETED) is False


def test_running_can_transition_to_completed():
    """Verify RUNNING allows transition to COMPLETED."""
    assert JobRunStatus.RUNNING.can_transition_to(JobRunStatus.COMPLETED) is True


def test_running_can_transition_to_failed():
    """Verify RUNNING allows transition to FAILED."""
    assert JobRunStatus.RUNNING.can_transition_to(JobRunStatus.FAILED) is True


def test_running_can_transition_to_cancelled():
    """Verify RUNNING allows transition to CANCELLED."""
    assert JobRunStatus.RUNNING.can_transition_to(JobRunStatus.CANCELLED) is True


def test_running_cannot_transition_to_pending():
    """Verify RUNNING does not allow transition back to PENDING."""
    assert JobRunStatus.RUNNING.can_transition_to(JobRunStatus.PENDING) is False


@pytest.mark.parametrize("target", list(JobRunStatus))
def test_completed_is_terminal(target: JobRunStatus):
    """Verify COMPLETED cannot transition to any state."""
    assert JobRunStatus.COMPLETED.can_transition_to(target) is False


@pytest.mark.parametrize("target", list(JobRunStatus))
def test_failed_is_terminal(target: JobRunStatus):
    """Verify FAILED cannot transition to any state."""
    assert JobRunStatus.FAILED.can_transition_to(target) is False


@pytest.mark.parametrize("target", list(JobRunStatus))
def test_cancelled_is_terminal(target: JobRunStatus):
    """Verify CANCELLED cannot transition to any state."""
    assert JobRunStatus.CANCELLED.can_transition_to(target) is False
