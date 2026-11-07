"""Tests for the shared maintenance vocabulary."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import TableId, TableName


def test_maintenance_operation_ordered_follows_spec_order():
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
    assert TableName("iceberg", "a.b", "t").qualified() == "a.b.t"


def test_table_name_fully_qualified_includes_the_catalog():
    assert TableName("iceberg", "a.b", "t").fully_qualified() == "iceberg.a.b.t"


def test_table_name_rejects_empty_table():
    with pytest.raises(ValueError):
        TableName("iceberg", "a.b", "")


def test_table_uuid_wraps_value():
    assert str(TableId("abc")) == "abc"
