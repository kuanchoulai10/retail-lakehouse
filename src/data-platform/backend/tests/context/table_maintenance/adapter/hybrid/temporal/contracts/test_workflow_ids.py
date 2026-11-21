"""Tests for the Temporal workflow identifiers and the task queue."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    table_discovery_adhoc_workflow_id,
    table_discovery_schedule_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    table_maintenance_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    table_reconciliation_workflow_id,
)


def test_workflow_ids():
    """Reconciliation ids embed the table uuid."""
    assert table_reconciliation_workflow_id("u1") == "table-reconciliation:table-uuid=u1"
    assert TASK_QUEUE == "table-maintenance"


def test_workflow_id_names_the_table_uuid():
    """A table's maintenance runs one after another under one id, named by the table uuid."""
    uuid = "0b6c5e1a-7d2f-4c8e-9a3b-1f4e6d8c2a90"
    assert table_maintenance_workflow_id(uuid) == f"table-maintenance:table-uuid={uuid}"


def test_discovery_adhoc_workflow_id():
    """The ad hoc discovery id names the catalog, the optional namespace and the ad hoc trigger."""
    assert table_discovery_adhoc_workflow_id("c", "ns") == "table-discovery:catalog=c:namespace=ns:trigger=adhoc"
    assert table_discovery_adhoc_workflow_id("c", None) == "table-discovery:catalog=c:trigger=adhoc"


def test_discovery_adhoc_workflow_id_differs_from_the_schedule_id():
    """An ad hoc discovery run never shares the id of the catalog schedule."""
    assert table_discovery_adhoc_workflow_id("c", None) != table_discovery_schedule_id("c")


def test_discovery_schedule_id_is_per_catalog():
    """The discovery schedule id is the shared prefix followed by the catalog name."""
    assert table_discovery_schedule_id("iceberg") == "table-discovery:catalog=iceberg"
    assert table_discovery_schedule_id("iceberg").startswith(TABLE_DISCOVERY_SCHEDULE_ID_PREFIX)


def test_change_id_names_the_adhoc_workflow():
    """A scan started by a discovery policy change has its own id per change, apart from any other ad hoc run."""
    assert (
        table_discovery_adhoc_workflow_id("iceberg", None, change_id="ab12")
        == "table-discovery:catalog=iceberg:trigger=policy-changed:change=ab12"
    )
    assert table_discovery_adhoc_workflow_id("c", None, change_id="ab12") != table_discovery_adhoc_workflow_id(
        "c", None
    )
    assert table_discovery_adhoc_workflow_id("c", None, change_id="ab12") != table_discovery_adhoc_workflow_id(
        "c", None, change_id="cd34"
    )
