"""Test the glob pattern that selects tables by catalog, namespace and name."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TablePattern,
)


def test_defaults_match_all():
    """A pattern without arguments matches every table."""
    assert TablePattern().matches(TableName(catalog="c", namespace="n", table="t"))


def test_pattern_matches_globs():
    """A pattern matches table names by glob on each part and rejects the others."""
    p = TablePattern(catalog="iceberg", namespace="sales*", table="*_raw")
    assert p.matches(TableName(catalog="iceberg", namespace="sales_eu", table="orders_raw"))
    assert not p.matches(TableName(catalog="iceberg", namespace="inventory", table="orders_raw"))
    assert not p.matches(TableName(catalog="other", namespace="sales_eu", table="orders_raw"))
    assert not p.matches(TableName(catalog="iceberg", namespace="sales_eu", table="orders"))


def test_matching_is_case_sensitive():
    """Pattern matching is case sensitive."""
    assert not TablePattern(catalog="iceberg", namespace="Sales*").matches(
        TableName(catalog="iceberg", namespace="sales_eu", table="t")
    )
