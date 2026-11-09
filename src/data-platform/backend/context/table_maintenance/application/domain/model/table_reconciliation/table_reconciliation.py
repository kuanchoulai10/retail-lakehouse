"""Define the TableReconciliation aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table_reconciliation.invalid_reconciliation import (
    InvalidReconciliation,
)
from context.table_maintenance.application.domain.model.table_reconciliation.operation_result import (
    OperationResult,
)
from context.table_maintenance.application.domain.model.table_reconciliation.reconciliation_outcome import (
    ReconciliationOutcome,
)
from context.table_maintenance.application.domain.model.table_reconciliation.table_reconciliation_id import (
    TableReconciliationId,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        TableMaintenanceRunId,
    )
    from context.table_maintenance.application.domain.model.table_reconciliation.operation_outcome import (
        OperationOutcome,
    )
    from context.table_maintenance.application.domain.model.table_reconciliation.wake_reason import (
        WakeReason,
    )


@dataclass(eq=False)
class TableReconciliation(AggregateRoot[TableReconciliationId]):
    """Record one pass of the reconciler over a table and what it decided."""

    id: TableReconciliationId
    table_uuid: TableId
    reconciled_at: datetime
    wake_reasons: dict[WakeReason, int]
    dry_run: bool
    outcome: ReconciliationOutcome
    skip_reason: str | None
    operations: tuple[OperationOutcome, ...]
    run_id: TableMaintenanceRunId | None

    @classmethod
    def record(
        cls,
        id: TableReconciliationId,  # noqa: A002
        table_uuid: TableId,
        reconciled_at: datetime,
        wake_reasons: Mapping[WakeReason, int],
        dry_run: bool,  # noqa: FBT001
        outcome: ReconciliationOutcome,
        skip_reason: str | None,
        operations: Iterable[OperationOutcome],
        run_id: TableMaintenanceRunId | None,
    ) -> TableReconciliation:
        """Record a reconciliation, rejecting combinations that cannot happen."""
        if not wake_reasons:
            msg = "a reconciliation needs at least one wake reason"
            raise InvalidReconciliation(msg)
        if any(count < 1 for count in wake_reasons.values()):
            msg = "each wake reason must have been counted at least once"
            raise InvalidReconciliation(msg)
        ops = tuple(operations)
        if outcome is ReconciliationOutcome.SKIPPED:
            if not skip_reason:
                msg = "a skipped reconciliation needs a skip reason"
                raise InvalidReconciliation(msg)
            if ops:
                msg = "a skipped reconciliation assessed no operations"
                raise InvalidReconciliation(msg)
        elif skip_reason is not None:
            msg = "a planned reconciliation has no skip reason"
            raise InvalidReconciliation(msg)
        started = any(op.result is OperationResult.STARTED for op in ops)
        if run_id is not None and not started:
            msg = "a run id needs a started operation"
            raise InvalidReconciliation(msg)
        if started and run_id is None:
            msg = "a started operation needs the run id it started"
            raise InvalidReconciliation(msg)
        position = {op: i for i, op in enumerate(MaintenanceOperation.ordered())}
        return cls(
            id=id,
            table_uuid=table_uuid,
            reconciled_at=reconciled_at,
            wake_reasons=dict(wake_reasons),
            dry_run=dry_run,
            outcome=outcome,
            skip_reason=skip_reason,
            operations=tuple(sorted(ops, key=lambda o: position[o.operation])),
            run_id=run_id,
        )
