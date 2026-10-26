"""Tests for the shared maintenance vocabulary."""

from __future__ import annotations

import pytest

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance.workflow_ids import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    TABLE_DISCOVERY_SCHEDULE_ID,
    SIGNAL_ADMISSION_GRANTED,
    TASK_QUEUE,
    table_discovery_adhoc_workflow_id,
    table_discovery_schedule_id,
    table_maintenance_workflow_id,
    table_reconciliation_workflow_id,
)
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_uuid import TableUuid


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


def test_workflow_ids():
    assert table_reconciliation_workflow_id("u1") == "table-reconcile-u1"
    assert table_maintenance_workflow_id("r1") == "maintenance-r1"
    assert TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID == "maintenance-capacity"
    assert TABLE_DISCOVERY_SCHEDULE_ID == "table-discovery"
    assert TASK_QUEUE == "table-maintenance"
    assert SIGNAL_ADMISSION_GRANTED == "admission_granted"


def test_discovery_adhoc_workflow_id():
    assert table_discovery_adhoc_workflow_id("c", "ns") == "table-discovery-adhoc-c-ns"
    assert table_discovery_adhoc_workflow_id("c", None) == "table-discovery-adhoc-c-all"


def test_discovery_schedule_id_is_per_catalog():
    assert table_discovery_schedule_id("iceberg") == "table-discovery-iceberg"


def test_table_name_qualified():
    assert TableName("iceberg", "a.b", "t").qualified() == "a.b.t"


def test_table_name_rejects_empty_table():
    with pytest.raises(ValueError):
        TableName("iceberg", "a.b", "")


def test_table_uuid_wraps_value():
    assert str(TableUuid("abc")) == "abc"
