"""Test the Temporal workflow contracts round-trip through the default converter."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest
from temporalio.converter import DataConverter

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_MAX_ATTEMPTS,
    TABLE_MAINTENANCE_WORKFLOW,
    OperationResultSignal,
    TableMaintenanceWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationWorkflowInput,
)

RUN_IDS = ["mr-00000000000000000000000001", "mr-00000000000000000000000002"]
SETTINGS = {"attempt_deadline_seconds": 21600, "max_attempts": 3, "queue_wait_limit_seconds": 86400}


def _round_trip(value: object) -> object:
    async def go() -> object:
        converter = DataConverter.default
        payloads = await converter.encode([value])
        return (await converter.decode(payloads, [type(value)]))[0]

    return asyncio.run(go())


def test_contracts_round_trip():
    """Each contract survives a round trip through the Temporal payload converter unchanged."""
    plan = {"status": "planned", "operations": [{"operation": "rewrite_data_files"}, {"operation": "expire_snapshots"}]}
    values = [
        TableReconciliationWorkflowInput("u1"),
        TableReconciliationWorkflowInput(
            "u1",
            in_flight_run_ids=RUN_IDS,
            in_flight_started_at="2026-10-24T00:00:00+00:00",
            in_flight_operation_count=2,
            pending_manual=["expire_snapshots"],
            next_plan_at="2026-10-24T01:00:00+00:00",
            schedule_interval_seconds=600,
            continue_as_new_after=5,
            catalog_commit_debounce_seconds=None,
            commit_window_closes_at="2026-10-24T00:05:00+00:00",
            pending_commits=3,
        ),
        TableDiscoveryWorkflowInput("iceberg"),
        TableDiscoveryWorkflowInput("iceberg", "sales"),
        TableMaintenanceWorkflowInput(
            RUN_IDS, "u1", "table-reconciliation:table-uuid=u1", "scheduled", plan, **SETTINGS
        ),
        OperationResultSignal(RUN_IDS[0], "x", 1, False, {"a": 1}, "err"),
    ]
    for value in values:
        assert _round_trip(value) == value


@pytest.mark.parametrize("missing", sorted(SETTINGS))
def test_maintenance_workflow_input_requires_the_attempt_settings(missing: str):
    """A maintenance workflow input names every attempt setting, as its parent always passes all three."""
    settings = {key: value for key, value in SETTINGS.items() if key != missing}
    with pytest.raises(TypeError, match=missing):
        TableMaintenanceWorkflowInput(RUN_IDS, "u1", "p", "scheduled", {}, **settings)


def test_reconciliation_input_defaults_the_in_flight_max_attempts():
    """A fresh reconciliation input, with no run in flight, carries the maintenance workflow's three attempts."""
    assert TableReconciliationWorkflowInput(table_uuid="u1").in_flight_max_attempts == DEFAULT_MAX_ATTEMPTS


def test_table_reconcile_workflow_input_defaults():
    """The table reconciliation input starts with no in-flight run."""
    value = TableReconciliationWorkflowInput("u1")
    assert value.in_flight_run_ids is None
    assert value.in_flight_started_at is None
    assert value.in_flight_operation_count == 0
    assert value.pending_manual is None
    assert value.next_plan_at is None
    assert value.schedule_interval_seconds == 3600
    assert value.catalog_commit_debounce_seconds == 300
    assert value.commit_window_closes_at is None
    assert value.pending_commits == 0
    assert value.continue_as_new_after == 200


@pytest.mark.parametrize(
    "value",
    [
        TableReconciliationWorkflowInput("u1"),
        TableMaintenanceWorkflowInput(RUN_IDS, "u1", "p", "scheduled", {}, **SETTINGS),
    ],
)
def test_contracts_are_frozen(value: Any):  # noqa: ANN401
    """Contract values reject attribute assignment."""
    field_name = dataclasses.fields(value)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, field_name, "changed")


def test_workflow_type_names():
    """The workflow type names are the stable wire names."""
    assert TABLE_DISCOVERY_WORKFLOW == "TableDiscoveryWorkflow"
    assert TABLE_RECONCILIATION_WORKFLOW == "TableReconciliationWorkflow"
    assert TABLE_MAINTENANCE_WORKFLOW == "TableMaintenanceWorkflow"
