"""Tests for JobStatus."""

import pytest

from application.domain.model.job import JobStatus


def test_enum_values():
    """Verify that all JobStatus members have the expected string values."""
    assert JobStatus.ACTIVE == "active"
    assert JobStatus.PAUSED == "paused"
    assert JobStatus.ARCHIVED == "archived"


def test_active_can_transition_to_paused():
    """Verify ACTIVE allows transition to PAUSED."""
    assert JobStatus.ACTIVE.can_transition_to(JobStatus.PAUSED) is True


def test_active_can_transition_to_archived():
    """Verify ACTIVE allows transition to ARCHIVED."""
    assert JobStatus.ACTIVE.can_transition_to(JobStatus.ARCHIVED) is True


def test_paused_can_transition_to_active():
    """Verify PAUSED allows transition to ACTIVE."""
    assert JobStatus.PAUSED.can_transition_to(JobStatus.ACTIVE) is True


def test_paused_can_transition_to_archived():
    """Verify PAUSED allows transition to ARCHIVED."""
    assert JobStatus.PAUSED.can_transition_to(JobStatus.ARCHIVED) is True


@pytest.mark.parametrize("target", list(JobStatus))
def test_archived_is_terminal(target: JobStatus):
    """Verify ARCHIVED cannot transition to any state."""
    assert JobStatus.ARCHIVED.can_transition_to(target) is False


def test_active_cannot_transition_to_active():
    """Verify ACTIVE cannot transition to itself."""
    assert JobStatus.ACTIVE.can_transition_to(JobStatus.ACTIVE) is False
