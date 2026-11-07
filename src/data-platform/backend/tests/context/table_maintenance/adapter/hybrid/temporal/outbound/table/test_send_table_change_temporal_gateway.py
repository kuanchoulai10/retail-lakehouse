"""Test SendTableChangeTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from temporalio.client import RPCError
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
    is_enrolled: bool,
    table_name: str = "iceberg.sales.orders",
    operations: list[str] | None = None,
) -> SendTableChangeGatewayInput:
    return SendTableChangeGatewayInput(
        table_uuid=table_uuid,
        table_name=table_name,
        change=change,
        is_enrolled=is_enrolled,
        operations=operations or [],
    )


@pytest.mark.parametrize(
    ("change", "signal"),
    [
        ("updated", TableReconciliationSignal.TABLE_UPDATED),
        ("settings_changed", TableReconciliationSignal.SETTINGS_CHANGED),
        ("paused", TableReconciliationSignal.PAUSE),
        ("resumed", TableReconciliationSignal.RESUME),
        ("stopped", TableReconciliationSignal.STOP),
    ],
)
def test_each_change_maps_to_its_signal(harness, change, signal):
    """Each table change is delivered to the reconciliation workflow as its own signal."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change(f"map-{change}", change, is_enrolled=True))
    assert _signals(harness, f"map-{change}") == [[signal, {}]]


_SIGNAL_BY_TABLE_CHANGE = {
    TableChange.UPDATED: [TableReconciliationSignal.TABLE_UPDATED, {}],
    TableChange.SETTINGS_CHANGED: [TableReconciliationSignal.SETTINGS_CHANGED, {}],
    TableChange.PAUSED: [TableReconciliationSignal.PAUSE, {}],
    TableChange.RESUMED: [TableReconciliationSignal.RESUME, {}],
    TableChange.STOPPED: [TableReconciliationSignal.STOP, {}],
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
    gateway.send(_change(uuid, change.value, is_enrolled=True))
    assert _signals(harness, uuid) == [_SIGNAL_BY_TABLE_CHANGE[change]]


def test_maintenance_requested_carries_the_operations(harness):
    """A maintenance request signal carries the requested operations."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(
        _change(
            "trigger",
            "maintenance_requested",
            is_enrolled=True,
            operations=["expire_snapshots", "rewrite_data_files"],
        )
    )
    assert _signals(harness, "trigger") == [
        [
            TableReconciliationSignal.TRIGGER_NOW,
            {"operations": ["expire_snapshots", "rewrite_data_files"]},
        ]
    ]


def test_pause_of_an_enrolled_table_starts_the_missing_workflow_paused(harness):
    """Pausing an enrolled table whose workflow is missing starts it and then delivers the pause."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    assert not _workflow_exists(harness, "pause-start")
    gateway.send(_change("pause-start", "paused", is_enrolled=True))
    assert _signals(harness, "pause-start") == [[TableReconciliationSignal.PAUSE, {}]]


def test_enrolled_changes_start_one_workflow_and_deliver_both(harness):
    """Two changes to an enrolled table start one workflow and deliver both signals to it."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    for change in ("settings_changed", "updated"):
        gateway.send(_change("swl", change, is_enrolled=True))

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
        TableReconciliationSignal.SETTINGS_CHANGED,
        TableReconciliationSignal.TABLE_UPDATED,
    ]


def test_start_sets_the_table_summary_only_on_the_first_start(harness):
    """The workflow summary names the table and is set by the first start only."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    for table_name in ("iceberg.sales.orders", "iceberg.sales.renamed"):
        gateway.send(_change("summary", "settings_changed", is_enrolled=True, table_name=table_name))

    async def summary() -> str | None:
        handle = harness.client.get_workflow_handle(table_reconciliation_workflow_id("summary"))
        return await (await handle.describe()).static_summary()

    assert harness.bridge.run(summary) == "iceberg.sales.orders"


def test_not_enrolled_change_reaches_a_running_workflow(harness):
    """A change to a table that is not enrolled is still delivered to a running workflow."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("plain", "settings_changed", is_enrolled=True))
    gateway.send(_change("plain", "stopped", is_enrolled=False))
    assert [s for s, _ in _signals(harness, "plain", want=2)] == [
        TableReconciliationSignal.SETTINGS_CHANGED,
        TableReconciliationSignal.STOP,
    ]


def test_not_enrolled_change_never_starts_a_workflow(harness):
    """A change to a table that is not enrolled does not start a workflow."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("missing", "stopped", is_enrolled=False))
    assert not _workflow_exists(harness, "missing")


def test_unknown_change_is_rejected(harness):
    """An unknown table change is rejected with a ValueError."""
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    with pytest.raises(ValueError, match="unknown table change"):
        gateway.send(_change("unknown", "renamed", is_enrolled=True))
