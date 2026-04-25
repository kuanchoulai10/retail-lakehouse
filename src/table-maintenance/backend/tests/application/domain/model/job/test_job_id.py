"""Tests for JobId."""

from core.base import EntityId
from core.application.domain.model.job import JobId


def test_job_id_is_entity_id():
    """Verify that JobId is a subclass of EntityId."""
    assert issubclass(JobId, EntityId)


def test_job_id_value():
    """Verify that JobId stores its value and converts to string."""
    jid = JobId(value="abc1234567")
    assert jid.value == "abc1234567"
    assert str(jid) == "abc1234567"


def test_job_id_equality():
    """Verify that two JobIds with the same value are equal."""
    a = JobId(value="abc1234567")
    b = JobId(value="abc1234567")
    assert a == b


def test_job_id_inequality():
    """Verify that two JobIds with different values are not equal."""
    a = JobId(value="abc1234567")
    b = JobId(value="xyz9876543")
    assert a != b
