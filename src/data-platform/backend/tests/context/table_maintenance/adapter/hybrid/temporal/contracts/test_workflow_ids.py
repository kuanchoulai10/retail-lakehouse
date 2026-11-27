"""Tests for the Temporal workflow identifiers and the task queue."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID,
    table_discovery_adhoc_workflow_id,
    table_discovery_catalog_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TABLE_DISCOVERY_ROUND_WORKFLOW_ID,
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


def test_discovery_catalog_workflow_id():
    """A catalog has one scan id, shared by the round's scans and the scans a change requests."""
    assert table_discovery_catalog_workflow_id("iceberg") == "table-discovery:catalog=iceberg"


def test_discovery_adhoc_workflow_id():
    """The ad hoc discovery id of a namespace names the catalog, the namespace and the ad hoc trigger."""
    assert table_discovery_adhoc_workflow_id("c", "ns") == "table-discovery:catalog=c:namespace=ns:trigger=adhoc"


def test_a_namespace_scan_never_shares_the_catalog_scan_id():
    """A namespace scan runs beside the catalog's scan, never under its id."""
    assert table_discovery_adhoc_workflow_id("c", "ns") != table_discovery_catalog_workflow_id("c")
    assert table_discovery_adhoc_workflow_id("c", "ns", change_id="ab12") != table_discovery_catalog_workflow_id("c")


def test_discovery_ids_differ_from_the_schedule_and_round_ids():
    """The one discovery schedule and the round it starts have ids no catalog scan has."""
    assert table_discovery_catalog_workflow_id("round") != TABLE_DISCOVERY_ROUND_WORKFLOW_ID
    assert table_discovery_catalog_workflow_id("c") != TABLE_DISCOVERY_SCHEDULE_ID


def test_change_id_names_the_adhoc_workflow():
    """A namespace scan started by a discovery policy change has its own id per change."""
    assert (
        table_discovery_adhoc_workflow_id("iceberg", "sales", change_id="ab12")
        == "table-discovery:catalog=iceberg:namespace=sales:trigger=policy-changed:change=ab12"
    )
    assert table_discovery_adhoc_workflow_id("c", "ns", change_id="ab12") != table_discovery_adhoc_workflow_id(
        "c", "ns"
    )
    assert table_discovery_adhoc_workflow_id("c", "ns", change_id="ab12") != table_discovery_adhoc_workflow_id(
        "c", "ns", change_id="cd34"
    )
