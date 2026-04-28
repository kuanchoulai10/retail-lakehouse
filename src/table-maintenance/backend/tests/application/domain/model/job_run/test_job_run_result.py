"""Tests for JobRunResult."""

from __future__ import annotations

from base import ValueObject
from application.domain.model.job_run.job_run_result import JobRunResult


def test_is_value_object():
    """Verify that JobRunResult is a ValueObject."""
    assert issubclass(JobRunResult, ValueObject)


def test_fields():
    """Verify that all fields are stored correctly."""
    result = JobRunResult(
        duration_ms=1500,
        metadata={"expired_snapshots": "42"},
    )
    assert result.duration_ms == 1500
    assert result.metadata == {"expired_snapshots": "42"}


def test_none_duration():
    """Verify that duration_ms can be None."""
    result = JobRunResult(duration_ms=None, metadata={})
    assert result.duration_ms is None


def test_equality_by_value():
    """Verify that two results with same values are equal."""
    a = JobRunResult(duration_ms=100, metadata={"k": "v"})
    b = JobRunResult(duration_ms=100, metadata={"k": "v"})
    assert a == b


def test_immutable():
    """Verify that JobRunResult is frozen."""
    import pytest

    result = JobRunResult(duration_ms=100, metadata={})
    with pytest.raises(AttributeError):
        result.duration_ms = 200  # type: ignore[misc]  # ty: ignore[invalid-assignment]
