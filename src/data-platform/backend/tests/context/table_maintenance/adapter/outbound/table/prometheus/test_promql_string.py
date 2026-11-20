"""Test the promql_string function."""

from __future__ import annotations

from context.table_maintenance.adapter.outbound.table.prometheus import promql_string


def test_promql_string_escapes() -> None:
    """A quote, a backslash and a newline are escaped inside the double quotes."""
    assert promql_string('a"b\\c\nd') == '"a\\"b\\\\c\\nd"'


def test_promql_string_quotes_a_plain_value() -> None:
    """A plain value is only wrapped in double quotes."""
    assert promql_string("u1") == '"u1"'
