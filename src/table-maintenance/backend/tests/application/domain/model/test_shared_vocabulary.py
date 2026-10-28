"""Tests for the shared maintenance vocabulary."""

from __future__ import annotations

import pytest

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance.workflow_ids import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    SIGNAL_ADMISSION_GRANTED,
    TASK_QUEUE,
    table_discovery_adhoc_workflow_id,
    table_discovery_schedule_id,
    table_maintenance_workflow_id,
    table_reconciliation_workflow_id,
)
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_id import TableId


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
    assert (
        table_reconciliation_workflow_id("u1") == "table-reconciliation:table-uuid=u1"
    )
    assert (
        table_maintenance_workflow_id("iceberg.e2e.orders", "r1")
        == "table-maintenance:table=iceberg.e2e.orders:run=r1"
    )
    assert TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID == "table-maintenance-admission"
    assert TASK_QUEUE == "table-maintenance"
    assert SIGNAL_ADMISSION_GRANTED == "admission_granted"


def test_discovery_adhoc_workflow_id():
    assert (
        table_discovery_adhoc_workflow_id("c", "ns")
        == "table-discovery:catalog=c:namespace=ns:trigger=adhoc"
    )
    assert (
        table_discovery_adhoc_workflow_id("c", None)
        == "table-discovery:catalog=c:trigger=adhoc"
    )


def test_discovery_adhoc_workflow_id_differs_from_the_schedule_id():
    assert table_discovery_adhoc_workflow_id("c", None) != table_discovery_schedule_id(
        "c"
    )


def test_discovery_schedule_id_is_per_catalog():
    assert table_discovery_schedule_id("iceberg") == "table-discovery:catalog=iceberg"
    assert table_discovery_schedule_id("iceberg").startswith(
        TABLE_DISCOVERY_SCHEDULE_ID_PREFIX
    )


def test_table_name_qualified():
    assert TableName("iceberg", "a.b", "t").qualified() == "a.b.t"


def test_table_name_fully_qualified_includes_the_catalog():
    assert TableName("iceberg", "a.b", "t").fully_qualified() == "iceberg.a.b.t"


def test_table_name_rejects_empty_table():
    with pytest.raises(ValueError):
        TableName("iceberg", "a.b", "")


def test_table_uuid_wraps_value():
    assert str(TableId("abc")) == "abc"
