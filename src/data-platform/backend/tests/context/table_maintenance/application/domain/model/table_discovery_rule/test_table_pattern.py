"""Test the glob pattern that selects tables by catalog, namespace and name."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TablePattern,
)


def test_defaults_match_all():
    """A pattern without arguments matches every table."""
    assert TablePattern().matches(TableName("c", "n", "t"))


def test_pattern_matches_globs():
    """A pattern matches table names by glob on each part and rejects the others."""
    p = TablePattern("iceberg", "sales*", "*_raw")
    assert p.matches(TableName("iceberg", "sales_eu", "orders_raw"))
    assert not p.matches(TableName("iceberg", "inventory", "orders_raw"))
    assert not p.matches(TableName("other", "sales_eu", "orders_raw"))
    assert not p.matches(TableName("iceberg", "sales_eu", "orders"))


def test_matching_is_case_sensitive():
    """Pattern matching is case sensitive."""
    assert not TablePattern("iceberg", "Sales*").matches(TableName("iceberg", "sales_eu", "t"))
