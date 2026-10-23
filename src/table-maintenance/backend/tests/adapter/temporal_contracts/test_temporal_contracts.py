"""Test the Temporal workflow contracts round-trip through the default converter."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest
from temporalio.converter import DataConverter

from adapter.temporal_contracts import (
    CapacityAcquireSignal,
    CapacityLimiterInput,
    CapacityReleaseSignal,
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
    plan = {"status": "planned", "operations": [{"operation": "rewrite_data_files"}]}
    values = [
        TableReconcileWorkflowInput("u1"),
        DiscoveryWorkflowInput("iceberg"),
        DiscoveryWorkflowInput("iceberg", "sales"),
        MaintenanceWorkflowInput("r1", "u1", "table-reconcile-u1", "scheduled", plan),
        CapacityLimiterInput(2),
        CapacityLimiterInput(
            2,
            60,
            {
                "r1": {
                    "requester_workflow_id": "w1",
                    "granted_at": "2026-10-24T00:00:00+00:00",
                }
            },
            [{"request_id": "r2", "requester_workflow_id": "w2"}],
        ),
        CapacityAcquireSignal("r1", "w1"),
        CapacityReleaseSignal("r1"),
        OperationResultSignal("r1", "x", 1, False, {"a": 1}, "err"),
    ]
    for value in values:
        assert _round_trip(value) == value


def test_maintenance_workflow_input_default_attempt_deadline():
    value = MaintenanceWorkflowInput("r1", "u1", "p", "scheduled", {})
    assert value.attempt_deadline_seconds == 21600


def test_capacity_limiter_defaults():
    limiter = CapacityLimiterInput(1)
    assert limiter.lease_seconds == 21600
    assert limiter.holders == {}
    assert limiter.queue == []
    assert limiter.holders is not CapacityLimiterInput(1).holders
    assert limiter.queue is not CapacityLimiterInput(1).queue


@pytest.mark.parametrize(
    "value",
    [
        CapacityAcquireSignal("r1", "w1"),
        CapacityLimiterInput(1),
        CapacityReleaseSignal("r1"),
        MaintenanceWorkflowInput("r1", "u1", "p", "scheduled", {}),
    ],
)
def test_contracts_are_frozen(value: Any):  # noqa: ANN401
    field_name = dataclasses.fields(value)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, field_name, "changed")
