"""Tests for JobRunId."""

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRunId
from core.base.entity_id import EntityId


def test_is_entity_id():
    """Verify that JobRunId is a subclass of EntityId."""
    assert issubclass(JobRunId, EntityId)


def test_equality_by_value():
    """Verify that two JobRunIds with the same value are equal."""
    a = JobRunId(value="run-1")
    b = JobRunId(value="run-1")
    assert a == b


def test_inequality_different_value():
    """Verify that two JobRunIds with different values are not equal."""
    a = JobRunId(value="run-1")
    b = JobRunId(value="run-2")
    assert a != b


def test_typed_distinct_from_job_id():
    """Verify that a JobRunId is not equal to a JobId with the same value."""
    run_id = JobRunId(value="same-value")
    job_id = JobId(value="same-value")
    assert run_id != job_id
