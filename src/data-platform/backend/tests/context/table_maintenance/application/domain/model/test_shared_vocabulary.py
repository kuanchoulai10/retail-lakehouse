"""Tests for the shared maintenance vocabulary."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import TableId, TableName


def test_maintenance_operation_ordered_follows_spec_order():
    """The maintenance operations are ordered as the specification lists them."""
    assert MaintenanceOperation.ordered() == (
        MaintenanceOperation.REWRITE_DATA_FILES,
        MaintenanceOperation.REWRITE_MANIFESTS,
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        MaintenanceOperation.REMOVE_ORPHAN_FILES,
    )
    assert [str(op) for op in MaintenanceOperation.ordered()] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]


def test_table_name_qualified():
    """A table name is qualified by its namespace."""
    assert TableName(catalog="iceberg", namespace="a.b", table="t").qualified() == "a.b.t"


def test_table_name_fully_qualified_includes_the_catalog():
    """The fully qualified table name starts with the catalog."""
    assert TableName(catalog="iceberg", namespace="a.b", table="t").fully_qualified() == "iceberg.a.b.t"


def test_table_name_rejects_empty_table():
    """A table name with an empty table part is rejected."""
    with pytest.raises(ValueError):
        TableName(catalog="iceberg", namespace="a.b", table="")


def test_table_uuid_wraps_value():
    """A table id wraps its value and prints it."""
    assert str(TableId("abc")) == "abc"
