"""Test summary_int."""

from __future__ import annotations

from context.table_maintenance.application.service.table import summary_int


def test_numeric_value_is_parsed() -> None:
    """A numeric string value is parsed to an int."""
    assert summary_int({"added-records": "12"}, "added-records") == 12


def test_missing_key_is_none() -> None:
    """A missing key gives None."""
    assert summary_int({}, "added-records") is None


def test_non_numeric_value_is_none() -> None:
    """A non-numeric value gives None."""
    assert summary_int({"added-records": "abc"}, "added-records") is None
