"""Tests for JobsRepoAdapter."""

from configs import JobsRepoAdapter


def test_enum_values():
    """Verify that JobsRepoAdapter members have correct string values."""
    assert JobsRepoAdapter.IN_MEMORY == "in_memory"
    assert JobsRepoAdapter.SQL == "sql"


def test_is_str_enum():
    """Verify that JobsRepoAdapter members are str instances."""
    assert isinstance(JobsRepoAdapter.IN_MEMORY, str)
    assert isinstance(JobsRepoAdapter.SQL, str)
