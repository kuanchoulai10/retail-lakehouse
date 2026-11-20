"""Test SendTableChangeTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from temporalio.client import RPCError
from temporalio.common import SearchAttributeKey
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendTableChangeTemporalGateway,
)
from context.table_maintenance.application.domain.model.table import TableChange
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)

if TYPE_CHECKING:
    from tests.context.table_maintenance.adapter.hybrid.temporal.outbound.shared.temporal_harness import TemporalHarness


def _signals(h: TemporalHarness, table_uuid: str, want: int = 1) -> list:
    handle = h.client.get_workflow_handle(table_reconciliation_workflow_id(table_uuid))

    async def query() -> list:
        return await handle.query("signals")

    got: list = []
    deadline = time.time() + 10
    while time.time() < deadline:
        got = h.bridge.run(query)
        if len(got) >= want:
            return got
        time.sleep(0.1)
    return got


def _workflow_exists(h: TemporalHarness, table_uuid: str) -> bool:
    handle = h.client.get_workflow_handle(table_reconciliation_workflow_id(table_uuid))

    async def describe() -> bool:
        try:
            await handle.describe()
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return False
            raise
        return True

    return h.bridge.run(describe)


def _change(
    table_uuid: str,
    change: str,
    *,
    is_managed: bool,
    table_name: str = "iceberg.sales.orders",
    operations: list[str] | None = None,
    priority: str | None = None,
) -> SendTableChangeGatewayInput:
    return SendTableChangeGatewayInput(
        table_uuid=table_uuid,
        table_name=table_name,
        change=change,
        is_managed=is_managed,
        operations=operations or [],
        priority=priority,
    )


@pytest.mark.parametrize(
    ("change", "signal"),
    [
        ("updated", TableReconciliationSignal.TABLE_UPDATED),
        ("policy_changed", TableReconciliationSignal.POLICY_CHANGED),
        ("stopped", TableReconciliationSignal.STOP),
        ("reconcile_requested", TableReconciliationSignal.RECONCILE_NOW),
        ("seen", TableReconciliationSignal.TABLE_SEEN),
        ("managed", TableReconciliationSignal.TABLE_MANAGED),
    ],
)
def test_each_change_maps_to_its_signal(harness, change, signal):
    """Each table change is delivered to the reconciliation workflow as its own signal."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change(f"map-{change}", change, is_managed=True))
    assert _signals(harness, f"map-{change}") == [[signal, {}]]


_SIGNAL_BY_TABLE_CHANGE = {
    TableChange.UPDATED: [TableReconciliationSignal.TABLE_UPDATED, {}],
    TableChange.POLICY_CHANGED: [TableReconciliationSignal.POLICY_CHANGED, {}],
    TableChange.STOPPED: [TableReconciliationSignal.STOP, {}],
    TableChange.RECONCILE_REQUESTED: [TableReconciliationSignal.RECONCILE_NOW, {}],
    TableChange.SEEN: [TableReconciliationSignal.TABLE_SEEN, {}],
    TableChange.MANAGED: [TableReconciliationSignal.TABLE_MANAGED, {}],
    TableChange.MAINTENANCE_REQUESTED: [
        TableReconciliationSignal.TRIGGER_NOW,
        {"operations": []},
    ],
}


@pytest.mark.parametrize("change", list(TableChange), ids=lambda c: c.value)
def test_every_table_change_member_is_sent_as_its_signal(harness, change):
    """Every member of the table change enum is delivered as the signal it maps to."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    uuid = f"member-{change.value}"
    gateway.send(_change(uuid, change.value, is_managed=True))
    assert _signals(harness, uuid) == [_SIGNAL_BY_TABLE_CHANGE[change]]


def test_maintenance_requested_carries_the_operations(harness):
    """A maintenance request signal carries the requested operations."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(
        _change(
            "trigger",
            "maintenance_requested",
            is_managed=True,
            operations=["expire_snapshots", "rewrite_data_files"],
        )
    )
    assert _signals(harness, "trigger") == [
        [
            TableReconciliationSignal.TRIGGER_NOW,
            {"operations": ["expire_snapshots", "rewrite_data_files"]},
        ]
    ]


def test_maintenance_requested_carries_the_priority_only_when_given(harness):
    """A maintenance request signal names the priority when one is given and leaves it out otherwise."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(
        _change("trigger-p0", "maintenance_requested", is_managed=True, operations=["expire_snapshots"], priority="P0")
    )
    gateway.send(_change("trigger-none", "maintenance_requested", is_managed=True, operations=["expire_snapshots"]))
    assert _signals(harness, "trigger-p0") == [
        [TableReconciliationSignal.TRIGGER_NOW, {"operations": ["expire_snapshots"], "priority": "P0"}]
    ]
    assert _signals(harness, "trigger-none") == [
        [TableReconciliationSignal.TRIGGER_NOW, {"operations": ["expire_snapshots"]}]
    ]


def test_change_of_a_managed_table_starts_the_missing_workflow(harness):
    """A change to a managed table whose workflow is missing starts it and then delivers the change."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    assert not _workflow_exists(harness, "seen-start")
    gateway.send(_change("seen-start", "seen", is_managed=True))
    assert _signals(harness, "seen-start") == [[TableReconciliationSignal.TABLE_SEEN, {}]]


def test_managed_signal_with_starts_the_workflow(harness):
    """A table that became managed starts its missing workflow with ``table_managed``."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    assert not _workflow_exists(harness, "managed-start")
    gateway.send(_change("managed-start", "managed", is_managed=True))
    assert _signals(harness, "managed-start") == [[TableReconciliationSignal.TABLE_MANAGED, {}]]


def test_managed_changes_start_one_workflow_and_deliver_both(harness):
    """Two changes to a managed table start one workflow and deliver both signals to it."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    for change in ("policy_changed", "updated"):
        gateway.send(_change("swl", change, is_managed=True))

    async def count() -> int:
        found = [
            w.id async for w in harness.client.list_workflows("WorkflowId = 'table-reconciliation:table-uuid=swl'")
        ]
        return len(found)

    found = harness.bridge.run(count)
    deadline = time.time() + 10
    while found < 1 and time.time() < deadline:
        time.sleep(0.1)
        found = harness.bridge.run(count)
    assert found == 1
    assert [s for s, _ in _signals(harness, "swl", want=2)] == [
        TableReconciliationSignal.POLICY_CHANGED,
        TableReconciliationSignal.TABLE_UPDATED,
    ]


def test_start_sets_the_table_summary_only_on_the_first_start(harness):
    """The workflow summary names the table and is set by the first start only."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    for table_name in ("iceberg.sales.orders", "iceberg.sales.renamed"):
        gateway.send(_change("summary", "policy_changed", is_managed=True, table_name=table_name))

    async def summary() -> str | None:
        handle = harness.client.get_workflow_handle(table_reconciliation_workflow_id("summary"))
        return await (await handle.describe()).static_summary()

    assert harness.bridge.run(summary) == "iceberg.sales.orders"


def test_unmanaged_change_reaches_a_running_workflow(harness):
    """A change to a table that is not managed is still delivered to a running workflow."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("plain", "policy_changed", is_managed=True))
    gateway.send(_change("plain", "stopped", is_managed=False))
    assert [s for s, _ in _signals(harness, "plain", want=2)] == [
        TableReconciliationSignal.POLICY_CHANGED,
        TableReconciliationSignal.STOP,
    ]


def test_unmanaged_change_never_starts_a_workflow(harness):
    """A change to a table that is not managed does not start a workflow."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("missing", "stopped", is_managed=False))
    assert not _workflow_exists(harness, "missing")


def test_unknown_change_is_rejected(harness):
    """An unknown table change is rejected with a ValueError."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    with pytest.raises(ValueError, match="unknown table change"):
        gateway.send(_change("unknown", "renamed", is_managed=True))


def test_send_table_change_starts_reconciliation_with_table_search_attributes(harness):
    """A reconciliation started for a managed table is tagged with the table's UUID and name."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("tagged", "seen", is_managed=True, table_name="iceberg.sales.tagged"))
    handle = harness.client.get_workflow_handle(table_reconciliation_workflow_id("tagged"))

    async def describe():
        return (await handle.describe()).typed_search_attributes

    attributes = harness.bridge.run(describe)
    assert attributes.get(SearchAttributeKey.for_keyword("TableUuid")) == "tagged"
    assert attributes.get(SearchAttributeKey.for_keyword("TableName")) == "iceberg.sales.tagged"
