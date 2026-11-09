"""Define the TableReconciliationRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.adapter.outbound.shared.sql import IsoDatetimeCodec
from context.table_maintenance.application.port.outbound.table_reconciliation import (
    ConditionCombine,
    MaintenanceOperation,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
    OperationOutcome,
    OperationResult,
    ReconciliationOutcome,
    TableId,
    TableMaintenanceRunId,
    TableReconciliation,
    TableReconciliationId,
    WakeReason,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


def _encode_measurement(m: Measurement) -> dict[str, Any]:
    return {
        "key": m.key,
        "observed": m.observed,
        "unit": m.unit.value,
        "threshold": m.threshold,
        "comparison": None if m.comparison is None else m.comparison.value,
    }


def _decode_measurement(data: dict[str, Any]) -> Measurement:
    comparison = data["comparison"]
    return Measurement(
        key=data["key"],
        observed=data["observed"],
        unit=MeasurementUnit(data["unit"]),
        threshold=data["threshold"],
        comparison=None if comparison is None else MeasurementComparison(comparison),
    )


def _encode_operation(op: OperationOutcome) -> dict[str, Any]:
    return {
        "operation": op.operation.value,
        "result": op.result.value,
        "combine": op.combine.value,
        "measurements": [_encode_measurement(m) for m in op.measurements],
        "next_eligible_at": IsoDatetimeCodec.encode(op.next_eligible_at),
    }


def _decode_operation(data: dict[str, Any]) -> OperationOutcome:
    return OperationOutcome(
        operation=MaintenanceOperation(data["operation"]),
        result=OperationResult(data["result"]),
        combine=ConditionCombine(data["combine"]),
        measurements=tuple(_decode_measurement(m) for m in data["measurements"]),
        next_eligible_at=IsoDatetimeCodec.decode(data["next_eligible_at"]),
    )


class TableReconciliationRowMapper:
    """Convert between TableReconciliation aggregates and table rows."""

    @staticmethod
    def to_values(rec: TableReconciliation) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": rec.id.value,
            "table_uuid": rec.table_uuid.value,
            "reconciled_at": rec.reconciled_at,
            "wake_reasons_json": {reason.value: count for reason, count in rec.wake_reasons.items()},
            "dry_run": rec.dry_run,
            "outcome": rec.outcome.value,
            "skip_reason": rec.skip_reason,
            "operations_json": [_encode_operation(op) for op in rec.operations],
            "run_id": None if rec.run_id is None else rec.run_id.value,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> TableReconciliation:
        """Rebuild the aggregate from a row."""
        run_id = row["run_id"]
        return TableReconciliation(
            id=TableReconciliationId(row["id"]),
            table_uuid=TableId(row["table_uuid"]),
            reconciled_at=row["reconciled_at"],
            wake_reasons={WakeReason(reason): count for reason, count in row["wake_reasons_json"].items()},
            dry_run=row["dry_run"],
            outcome=ReconciliationOutcome(row["outcome"]),
            skip_reason=row["skip_reason"],
            operations=tuple(_decode_operation(d) for d in row["operations_json"]),
            run_id=None if run_id is None else TableMaintenanceRunId(run_id),
        )
