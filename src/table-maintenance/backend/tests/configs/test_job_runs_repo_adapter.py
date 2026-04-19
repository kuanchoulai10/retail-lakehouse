"""Tests for JobRunsRepoAdapter."""

from configs import JobRunsRepoAdapter


def test_enum_values():
    """Verify that JobRunsRepoAdapter members have correct string values."""
    assert JobRunsRepoAdapter.IN_MEMORY == "in_memory"
    assert JobRunsRepoAdapter.SQL == "sql"


def test_is_str_enum():
    """Verify that JobRunsRepoAdapter members are str instances."""
    assert isinstance(JobRunsRepoAdapter.IN_MEMORY, str)
    assert isinstance(JobRunsRepoAdapter.SQL, str)
