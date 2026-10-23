"""Test the Temporal workflow contracts round-trip through the default converter."""

from __future__ import annotations

import asyncio

from temporalio.converter import DataConverter

from adapter.temporal_contracts import (
    CapacityLimiterInput,
    DiscoveryWorkflowInput,
    MaintenanceWorkflowInput,
    OperationResultSignal,
    TableReconcileWorkflowInput,
)


def _round_trip(value: object) -> object:
    async def go() -> object:
        converter = DataConverter.default
        payloads = await converter.encode([value])
        return (await converter.decode(payloads, [type(value)]))[0]

    return asyncio.run(go())


def test_contracts_round_trip():
    values = [
        TableReconcileWorkflowInput("u1"),
        DiscoveryWorkflowInput("iceberg"),
        DiscoveryWorkflowInput("iceberg", "sales"),
        MaintenanceWorkflowInput("r1", "u1", "scheduled", [{"operation": "x"}]),
        CapacityLimiterInput(2),
        CapacityLimiterInput(2, ["r1"]),
        OperationResultSignal("r1", "x", 1, False, {"a": 1}, "err"),
    ]
    for value in values:
        assert _round_trip(value) == value


def test_capacity_limiter_holders_default_is_not_shared():
    assert CapacityLimiterInput(1).holders == []
    assert CapacityLimiterInput(1).holders is not CapacityLimiterInput(1).holders
