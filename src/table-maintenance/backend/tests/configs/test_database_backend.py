"""Tests for DatabaseBackend."""

from bootstrap.configs import DatabaseBackend


def test_enum_values():
    """Verify that DatabaseBackend members have correct string values."""
    assert DatabaseBackend.SQLITE == "sqlite"
    assert DatabaseBackend.POSTGRES == "postgres"


def test_is_str_enum():
    """Verify that DatabaseBackend members are str instances."""
    assert isinstance(DatabaseBackend.SQLITE, str)
    assert isinstance(DatabaseBackend.POSTGRES, str)
