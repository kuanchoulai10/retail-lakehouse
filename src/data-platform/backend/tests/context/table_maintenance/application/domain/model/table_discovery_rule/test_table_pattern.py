from __future__ import annotations

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TablePattern,
)
from context.table_maintenance.application.domain.model.table import TableName


def test_defaults_match_all():
    assert TablePattern().matches(TableName("c", "n", "t"))


def test_pattern_matches_globs():
    p = TablePattern("iceberg", "sales*", "*_raw")
    assert p.matches(TableName("iceberg", "sales_eu", "orders_raw"))
    assert not p.matches(TableName("iceberg", "inventory", "orders_raw"))
    assert not p.matches(TableName("other", "sales_eu", "orders_raw"))
    assert not p.matches(TableName("iceberg", "sales_eu", "orders"))


def test_matching_is_case_sensitive():
    assert not TablePattern("iceberg", "Sales*").matches(
        TableName("iceberg", "sales_eu", "t")
    )
