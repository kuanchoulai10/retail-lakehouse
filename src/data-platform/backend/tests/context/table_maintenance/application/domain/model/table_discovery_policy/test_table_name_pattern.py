"""Test TableNamePattern: a glob on the table name only."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table_discovery_policy import TableNamePattern


def test_an_empty_pattern_is_refused() -> None:
    """An empty pattern is refused."""
    with pytest.raises(InvariantViolation):
        TableNamePattern(value="")


@pytest.mark.parametrize(
    ("pattern", "table", "expected"),
    [
        ("*", "orders", True),
        ("*_tmp", "refunds_tmp", True),
        ("*_tmp", "orders", False),
        ("orders", "orders", True),
        ("Orders", "orders", False),
        ("sales.*", "orders", False),
        ("order?", "orders", True),
    ],
)
def test_matches_the_table_name_case_sensitively(pattern: str, table: str, expected: bool) -> None:
    """Matches the table name case sensitively."""
    assert TableNamePattern(value=pattern).matches(table) is expected
