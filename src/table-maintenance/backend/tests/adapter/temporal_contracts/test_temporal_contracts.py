"""Test the Temporal workflow contracts round-trip through the default converter."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest
from temporalio.converter import DataConverter

from adapter.temporal_contracts import activity_names, workflow_names
from adapter.temporal_contracts import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
    DEFAULT_ADMISSION_LEASE_SECONDS,
    AdmissionAcquireSignal,
    TableMaintenanceAdmissionInput,
    AdmissionReleaseSignal,
    TableDiscoveryWorkflowInput,
    TableMaintenanceWorkflowInput,
    OperationResultSignal,
    TableReconciliationWorkflowInput,
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
        TableReconciliationWorkflowInput("u1"),
        TableReconciliationWorkflowInput(
            "u1",
            in_flight_run_id="r1",
            in_flight_started_at="2026-10-24T00:00:00+00:00",
            in_flight_operation_count=2,
            pending_manual=["expire_snapshots"],
            next_plan_at="2026-10-24T01:00:00+00:00",
            reconcile_interval_seconds=600,
            continue_as_new_after=5,
        ),
        TableDiscoveryWorkflowInput("iceberg"),
        TableDiscoveryWorkflowInput("iceberg", "sales"),
        TableMaintenanceWorkflowInput(
            "r1", "u1", "table-reconcile-u1", "scheduled", plan
        ),
        TableMaintenanceAdmissionInput(2),
        TableMaintenanceAdmissionInput(
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
        AdmissionAcquireSignal("r1", "w1"),
        AdmissionReleaseSignal("r1"),
        OperationResultSignal("r1", "x", 1, False, {"a": 1}, "err"),
    ]
    for value in values:
        assert _round_trip(value) == value


def test_maintenance_workflow_input_default_attempt_deadline():
    value = TableMaintenanceWorkflowInput("r1", "u1", "p", "scheduled", {})
    assert value.attempt_deadline_seconds == 21600 == DEFAULT_ATTEMPT_DEADLINE_SECONDS


def test_admission_lease_outlives_the_attempt_deadline_by_15_minutes():
    assert DEFAULT_ADMISSION_LEASE_SECONDS == DEFAULT_ATTEMPT_DEADLINE_SECONDS + 15 * 60
    assert (
        TableMaintenanceAdmissionInput(1).lease_seconds
        == DEFAULT_ADMISSION_LEASE_SECONDS
    )


def test_admission_input_defaults():
    admission = TableMaintenanceAdmissionInput(1)
    assert admission.lease_seconds == 22500
    assert admission.holders == {}
    assert admission.queue == []
    assert admission.holders is not TableMaintenanceAdmissionInput(1).holders
    assert admission.queue is not TableMaintenanceAdmissionInput(1).queue


def test_table_reconcile_workflow_input_defaults():
    value = TableReconciliationWorkflowInput("u1")
    assert value.in_flight_run_id is None
    assert value.in_flight_started_at is None
    assert value.in_flight_operation_count == 0
    assert value.pending_manual is None
    assert value.next_plan_at is None
    assert value.reconcile_interval_seconds == 3600
    assert value.continue_as_new_after == 200


@pytest.mark.parametrize(
    "value",
    [
        TableReconciliationWorkflowInput("u1"),
        AdmissionAcquireSignal("r1", "w1"),
        TableMaintenanceAdmissionInput(1),
        AdmissionReleaseSignal("r1"),
        TableMaintenanceWorkflowInput("r1", "u1", "p", "scheduled", {}),
    ],
)
def test_contracts_are_frozen(value: Any):  # noqa: ANN401
    field_name = dataclasses.fields(value)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, field_name, "changed")


def test_workflow_type_names():
    assert workflow_names.TABLE_DISCOVERY_WORKFLOW == "TableDiscoveryWorkflow"
    assert workflow_names.TABLE_RECONCILIATION_WORKFLOW == "TableReconciliationWorkflow"
    assert workflow_names.TABLE_MAINTENANCE_WORKFLOW == "TableMaintenanceWorkflow"
    assert (
        workflow_names.TABLE_MAINTENANCE_ADMISSION_WORKFLOW
        == "TableMaintenanceAdmissionWorkflow"
    )


def test_admission_activity_name():
    assert activity_names.SIGNAL_ADMISSION_ACQUIRE == "signal_admission_acquire"
