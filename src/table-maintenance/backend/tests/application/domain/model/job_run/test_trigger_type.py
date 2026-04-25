"""Tests for TriggerType."""

from core.application.domain.model.job_run import TriggerType


def test_enum_values():
    """Verify that all TriggerType members have the expected string values."""
    assert TriggerType.MANUAL == "manual"
    assert TriggerType.SCHEDULED == "scheduled"
