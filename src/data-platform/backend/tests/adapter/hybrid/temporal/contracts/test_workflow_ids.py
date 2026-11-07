"""Tests for the Temporal workflow identifiers and the task queue."""

from __future__ import annotations

from adapter.hybrid.temporal.contracts.shared import TASK_QUEUE
from adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    table_discovery_adhoc_workflow_id,
    table_discovery_schedule_id,
)
from adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceSignal,
    table_maintenance_workflow_id,
)
from adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
)
from adapter.hybrid.temporal.contracts.table_reconciliation import (
    table_reconciliation_workflow_id,
)


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
    assert TableMaintenanceSignal.ADMISSION_GRANTED == "admission_granted"


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
