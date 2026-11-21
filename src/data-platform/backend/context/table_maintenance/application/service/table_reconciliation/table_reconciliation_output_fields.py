"""Define the table_reconciliation_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import Measurement
    from context.table_maintenance.application.domain.model.table_reconciliation import (
        OperationOutcome,
        TableReconciliation,
    )


def table_reconciliation_output_fields(reconciliation: TableReconciliation, names: dict[str, str]) -> dict[str, Any]:
    """Return the output fields of one reconciliation, nested ones as dicts, for the list and the get output.

    ``names`` maps the ids of the policies that still exist to their current names; a policy missing
    from it has been deleted, and the record keeps the name it took when it was written.
    """
    return {
        "reconciliation_id": reconciliation.id.value,
        "table_uuid": reconciliation.table_uuid.value,
        "reconciled_at": reconciliation.reconciled_at,
        "wake_reasons": {reason.value: count for reason, count in reconciliation.wake_reasons.items()},
        "dry_run": reconciliation.dry_run,
        "outcome": reconciliation.outcome.value,
        "skip_reason": reconciliation.skip_reason,
        "operations": tuple(_operation(op) for op in reconciliation.operations),
        "policy_id": reconciliation.policy_id.value,
        "policy_name": names.get(reconciliation.policy_id.value, reconciliation.policy_name.value),
        "policy_deleted": reconciliation.policy_id.value not in names,
        "policy_version": reconciliation.policy_version,
        "policy_target": _policy_target(reconciliation),
    }


def _policy_target(reconciliation: TableReconciliation) -> dict[str, Any] | None:
    target = reconciliation.policy_target
    if target is None:
        return None
    return {"type": target.type.value, "path": tuple(target.path)}


def _operation(outcome: OperationOutcome) -> dict[str, Any]:
    return {
        "operation": outcome.operation.value,
        "result": outcome.result.value,
        "measurements": tuple(_measurement(m) for m in outcome.measurements),
        "next_eligible_at": outcome.next_eligible_at,
        "run_id": outcome.run_id.value if outcome.run_id else None,
    }


def _measurement(measurement: Measurement) -> dict[str, Any]:
    return {
        "key": measurement.key,
        "observed": measurement.observed,
        "unit": measurement.unit.value,
        "threshold": measurement.threshold,
        "comparison": measurement.comparison.value if measurement.comparison else None,
        "met": measurement.met,
    }
