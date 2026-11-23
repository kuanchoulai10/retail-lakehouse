"""Test the text a partition value is shown as."""

from __future__ import annotations

import pytest

from context.table_maintenance.adapter.inbound.web.table_maintenance_run import partition_value_text


@pytest.mark.parametrize(
    ("transform", "source_type", "value", "text"),
    [
        ("year", "date", 56, "2026"),
        ("year", "timestamptz", -1, "1969"),
        ("month", "date", 682, "2026-11"),
        ("month", "timestamp", -1, "1969-12"),
        ("day", "timestamptz", 20412, "2025-11-20"),
        ("day", "date", -1, "1969-12-31"),
        ("hour", "timestamp", 489240, "2025-10-24-00"),
        ("identity", "date", 20412, "2025-11-20"),
        ("identity", "timestamptz", 1_000_000, "1970-01-01T00:00:01+00:00"),
        ("identity", "timestamp", 1_500_000, "1970-01-01T00:00:01.500000"),
        ("identity", "boolean", True, "true"),
        ("identity", "boolean", False, "false"),
        ("identity", "string", "o'neil", "o'neil"),
        ("identity", "decimal(9,2)", "12.30", "12.30"),
        ("identity", "long", 7, "7"),
        ("identity", "double", 1.5, "1.5"),
        ("bucket[16]", "long", 3, "3"),
        ("truncate[4]", "string", "abcd", "abcd"),
    ],
)
def test_a_value_is_shown_in_iceberg_human_form(transform, source_type, value, text):
    """Time transforms show their period and identity times their instant, as Iceberg prints partitions."""
    assert partition_value_text(transform, source_type, value) == text


def test_a_null_value_stays_null():
    """A null partition is shown as null, not as text."""
    assert partition_value_text("day", "date", None) is None


@pytest.mark.parametrize(
    ("transform", "source_type", "value"),
    [("day", "date", 10**9), ("year", "date", 10**6), ("identity", "timestamp", 10**20), ("day", "date", "x")],
)
def test_a_value_no_calendar_holds_is_shown_as_it_is(transform, source_type, value):
    """A value that names no date is shown as the stored value, never as an error."""
    assert partition_value_text(transform, source_type, value) == str(value)
