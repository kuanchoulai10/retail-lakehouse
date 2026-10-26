"""Test SendTableSignalTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time

from adapter.outbound.workflow.temporal.send_table_signal_temporal_gateway import (
    SendTableSignalTemporalGateway,
)
from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_SETTINGS_CHANGED,
    SIGNAL_TABLE_UPDATED,
    table_reconciliation_workflow_id,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from tests.adapter.outbound.temporal.temporal_harness import TemporalHarness


def _signals(h: TemporalHarness, table_uuid: str) -> list:
    handle = h.client.get_workflow_handle(table_reconciliation_workflow_id(table_uuid))

    async def query() -> list:
        return await handle.query("signals")

    for _ in range(50):
        got = h.bridge.run(query)
        if got:
            return got
        time.sleep(0.1)
    return []


def test_signal_with_start_creates_one_workflow_and_delivers_both(harness):
    gateway = SendTableSignalTemporalGateway(harness.client, harness.bridge)
    for payload in ({"n": 1}, {"n": 2}):
        gateway.send(
            SendTableSignalGatewayInput(
                table_uuid="swl",
                signal=SIGNAL_SETTINGS_CHANGED,
                payload=payload,
                start_if_missing=True,
            )
        )

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
    got = _signals(harness, "swl")
    deadline = time.time() + 5
    while len(got) < 2 and time.time() < deadline:
        time.sleep(0.2)
        got = _signals(harness, "swl")
    assert [p for _, p in got] == [{"n": 1}, {"n": 2}]


def test_plain_signal_reaches_existing_workflow(harness):
    gateway = SendTableSignalTemporalGateway(harness.client, harness.bridge)
    gateway.send(
        SendTableSignalGatewayInput("plain", SIGNAL_SETTINGS_CHANGED, {}, True)
    )
    gateway.send(
        SendTableSignalGatewayInput("plain", SIGNAL_TABLE_UPDATED, {"x": 1}, False)
    )
    deadline = time.time() + 5
    got = _signals(harness, "plain")
    while len(got) < 2 and time.time() < deadline:
        time.sleep(0.2)
        got = _signals(harness, "plain")
    assert [s for s, _ in got] == [SIGNAL_SETTINGS_CHANGED, SIGNAL_TABLE_UPDATED]


def test_plain_signal_to_missing_workflow_does_not_raise(harness):
    gateway = SendTableSignalTemporalGateway(harness.client, harness.bridge)
    gateway.send(
        SendTableSignalGatewayInput("missing", SIGNAL_TABLE_UPDATED, {}, False)
    )
