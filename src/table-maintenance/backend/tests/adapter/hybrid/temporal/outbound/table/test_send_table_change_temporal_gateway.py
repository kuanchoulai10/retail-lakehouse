"""Test SendTableChangeTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time

import pytest
from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from adapter.hybrid.temporal.contracts.workflow_ids import (
    SIGNAL_PAUSE,
    SIGNAL_RESUME,
    SIGNAL_SETTINGS_CHANGED,
    SIGNAL_STOP,
    SIGNAL_TABLE_UPDATED,
    SIGNAL_TRIGGER_NOW,
    table_reconciliation_workflow_id,
)
from adapter.hybrid.temporal.outbound.table.send_table_change_temporal_gateway import (
    SendTableChangeTemporalGateway,
)
from application.domain.model.table import TableChange
from application.port.outbound.table.send_table_change import (
    SendTableChangeGatewayInput,
)
from tests.adapter.hybrid.temporal.outbound.shared.temporal_harness import (
    TemporalHarness,
)


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
        ("updated", SIGNAL_TABLE_UPDATED),
        ("settings_changed", SIGNAL_SETTINGS_CHANGED),
        ("paused", SIGNAL_PAUSE),
        ("resumed", SIGNAL_RESUME),
        ("stopped", SIGNAL_STOP),
    ],
)
def test_each_change_maps_to_its_signal(harness, change, signal):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change(f"map-{change}", change, is_enrolled=True))
    assert _signals(harness, f"map-{change}") == [[signal, {}]]


_SIGNAL_BY_TABLE_CHANGE = {
    TableChange.UPDATED: [SIGNAL_TABLE_UPDATED, {}],
    TableChange.SETTINGS_CHANGED: [SIGNAL_SETTINGS_CHANGED, {}],
    TableChange.PAUSED: [SIGNAL_PAUSE, {}],
    TableChange.RESUMED: [SIGNAL_RESUME, {}],
    TableChange.STOPPED: [SIGNAL_STOP, {}],
    TableChange.MAINTENANCE_REQUESTED: [SIGNAL_TRIGGER_NOW, {"operations": []}],
}


@pytest.mark.parametrize("change", list(TableChange), ids=lambda c: c.value)
def test_every_table_change_member_is_sent_as_its_signal(harness, change):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    uuid = f"member-{change.value}"
    gateway.send(_change(uuid, change.value, is_enrolled=True))
    assert _signals(harness, uuid) == [_SIGNAL_BY_TABLE_CHANGE[change]]


def test_maintenance_requested_carries_the_operations(harness):
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
            SIGNAL_TRIGGER_NOW,
            {"operations": ["expire_snapshots", "rewrite_data_files"]},
        ]
    ]


def test_pause_of_an_enrolled_table_starts_the_missing_workflow_paused(harness):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    assert not _workflow_exists(harness, "pause-start")
    gateway.send(_change("pause-start", "paused", is_enrolled=True))
    assert _signals(harness, "pause-start") == [[SIGNAL_PAUSE, {}]]


def test_enrolled_changes_start_one_workflow_and_deliver_both(harness):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    for change in ("settings_changed", "updated"):
        gateway.send(_change("swl", change, is_enrolled=True))

    async def count() -> int:
        found = [
            w.id
            async for w in harness.client.list_workflows(
                "WorkflowId = 'table-reconciliation:table-uuid=swl'"
            )
        ]
        return len(found)

    found = harness.bridge.run(count)
    deadline = time.time() + 10
    while found < 1 and time.time() < deadline:
        time.sleep(0.1)
        found = harness.bridge.run(count)
    assert found == 1
    assert [s for s, _ in _signals(harness, "swl", want=2)] == [
        SIGNAL_SETTINGS_CHANGED,
        SIGNAL_TABLE_UPDATED,
    ]


def test_start_sets_the_table_summary_only_on_the_first_start(harness):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    for table_name in ("iceberg.sales.orders", "iceberg.sales.renamed"):
        gateway.send(
            _change(
                "summary", "settings_changed", is_enrolled=True, table_name=table_name
            )
        )

    async def summary() -> str | None:
        handle = harness.client.get_workflow_handle(
            table_reconciliation_workflow_id("summary")
        )
        return await (await handle.describe()).static_summary()

    assert harness.bridge.run(summary) == "iceberg.sales.orders"


def test_not_enrolled_change_reaches_a_running_workflow(harness):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("plain", "settings_changed", is_enrolled=True))
    gateway.send(_change("plain", "stopped", is_enrolled=False))
    assert [s for s, _ in _signals(harness, "plain", want=2)] == [
        SIGNAL_SETTINGS_CHANGED,
        SIGNAL_STOP,
    ]


def test_not_enrolled_change_never_starts_a_workflow(harness):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    gateway.send(_change("missing", "stopped", is_enrolled=False))
    assert not _workflow_exists(harness, "missing")


def test_unknown_change_is_rejected(harness):
    gateway = SendTableChangeTemporalGateway(harness.client, harness.bridge)
    with pytest.raises(ValueError, match="unknown table change"):
        gateway.send(_change("unknown", "renamed", is_enrolled=True))
