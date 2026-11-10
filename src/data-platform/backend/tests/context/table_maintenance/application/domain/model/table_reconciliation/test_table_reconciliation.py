"""Tests for the TableReconciliation aggregate."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import (
    ConditionCombine,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_reconciliation import (
    OperationOutcome,
    OperationResult,
    ReconciliationOutcome,
    TableReconciliation,
    TableReconciliationId,
    WakeReason,
)

NOW = datetime(2026, 11, 10, 12, tzinfo=UTC)


def _outcome(op: Op, result: OperationResult = OperationResult.NOT_NEEDED) -> OperationOutcome:
    return OperationOutcome(
        operation=op,
        result=result,
        combine=ConditionCombine.ALL,
        measurements=(
            Measurement(
                key="small_files",
                observed=3,
                unit=MeasurementUnit.COUNT,
                threshold=10,
                comparison=MeasurementComparison.AT_LEAST,
            ),
        ),
    )


def _record(**overrides):
    args = {
        "id": TableReconciliationId("rec-1"),
        "table_uuid": TableId("t-1"),
        "reconciled_at": NOW,
        "wake_reasons": {WakeReason.SCHEDULE: 1},
        "dry_run": False,
        "outcome": ReconciliationOutcome.PLANNED,
        "skip_reason": None,
        "operations": (_outcome(Op.EXPIRE_SNAPSHOTS),),
        "run_id": None,
    }
    args.update(overrides)
    return TableReconciliation.record(**args)


def test_record_rejects_empty_wake_reasons():
    """A reconciliation needs at least one wake reason."""
    with pytest.raises(ValidationError):
        _record(wake_reasons={})


def test_record_rejects_wake_reason_count_below_one():
    """Each wake reason must have been counted at least once."""
    with pytest.raises(ValidationError):
        _record(wake_reasons={WakeReason.SCHEDULE: 0})


def test_record_rejects_skipped_without_skip_reason():
    """A skipped reconciliation says why."""
    with pytest.raises(ValidationError):
        _record(outcome=ReconciliationOutcome.SKIPPED, skip_reason=None, operations=())


def test_record_rejects_planned_with_skip_reason():
    """A planned reconciliation has no skip reason."""
    with pytest.raises(ValidationError):
        _record(skip_reason="paused")


def test_record_rejects_skipped_with_operations():
    """A skipped reconciliation assessed nothing."""
    with pytest.raises(ValidationError):
        _record(outcome=ReconciliationOutcome.SKIPPED, skip_reason="paused")


def test_record_rejects_run_id_without_started_operation():
    """A run id only makes sense when an operation started."""
    with pytest.raises(ValidationError):
        _record(run_id=TableMaintenanceRunId("run-1"))


def test_record_rejects_started_operation_without_run_id():
    """A started operation points at the run it started."""
    with pytest.raises(ValidationError):
        _record(operations=(_outcome(Op.EXPIRE_SNAPSHOTS, OperationResult.STARTED),))


def test_record_orders_operations_canonically():
    """Operations are stored in execution order."""
    rec = _record(operations=(_outcome(Op.EXPIRE_SNAPSHOTS), _outcome(Op.REWRITE_DATA_FILES)))
    assert [o.operation for o in rec.operations] == [Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS]


def test_started_operation_carries_the_run():
    """A started operation together with a run id is a valid record."""
    rec = _record(
        operations=(_outcome(Op.EXPIRE_SNAPSHOTS, OperationResult.STARTED),),
        run_id=TableMaintenanceRunId("run-1"),
    )
    assert rec.run_id == TableMaintenanceRunId("run-1")


def test_skipped_record_is_valid():
    """A skipped reconciliation with a reason and no operations is accepted."""
    rec = _record(outcome=ReconciliationOutcome.SKIPPED, skip_reason="paused", operations=())
    assert rec.skip_reason == "paused"


def test_direct_construction_checks_the_invariants():
    """Building the aggregate directly enforces the same rules as record."""
    with pytest.raises(ValidationError):
        TableReconciliation(
            id=TableReconciliationId("rec-1"),
            table_uuid=TableId("t-1"),
            reconciled_at=NOW,
            wake_reasons={},
            dry_run=False,
            outcome=ReconciliationOutcome.PLANNED,
            skip_reason=None,
            operations=(),
            run_id=None,
        )


def test_assigning_wrong_type_is_rejected():
    """A field assigned the wrong type raises ValidationError."""
    rec = _record()
    with pytest.raises(ValidationError):
        rec.reconciled_at = "yesterday"


def test_assignment_rechecks_invariants():
    """Assigning a run id without a started operation is rejected."""
    rec = _record()
    with pytest.raises(ValidationError):
        rec.run_id = TableMaintenanceRunId("run-1")
    assert rec.run_id is None


def test_operation_outcome_is_immutable():
    """An operation outcome cannot be changed after creation."""
    outcome = _outcome(Op.EXPIRE_SNAPSHOTS)
    with pytest.raises(ValidationError):
        outcome.result = OperationResult.OFF
