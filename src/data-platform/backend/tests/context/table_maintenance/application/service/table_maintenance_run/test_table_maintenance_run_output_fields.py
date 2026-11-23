"""Test table_maintenance_run_output_fields: what a run hands to its use case outputs."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.service.table_maintenance_run import table_maintenance_run_output_fields

NOW = datetime(2026, 11, 24, 12, tzinfo=UTC)


def test_run_output_fields_hand_out_plain_dicts() -> None:
    """The run's read-only arguments and metrics leave as plain dicts with the same content, ready for JSON."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId.new(),
        TableId("4504b45d-bea7-4a04-a5a3-08d369e83441"),
        TriggerType.SCHEDULED,
        MaintenanceOperation.REWRITE_DATA_FILES,
        NOW,
        execution_ref="wf-1",
        procedure_args={"a": {"b": 1}},
    )
    run.start_attempt(1, "job-1", NOW, size=ComputeSize.S)
    run.succeed(1, {"files": 3}, NOW)

    fields = table_maintenance_run_output_fields(run)

    assert type(fields["procedure_args"]) is dict
    assert type(fields["metrics"]) is dict
    assert fields["procedure_args"] == {"a": {"b": 1}}
    assert fields["metrics"] == {"files": 3}
    assert json.loads(json.dumps(fields["procedure_args"])) == {"a": {"b": 1}}
