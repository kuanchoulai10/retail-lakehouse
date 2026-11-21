"""Define the TableReconciliation aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import PositiveInt, model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    PolicyTarget,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_reconciliation.operation_outcome import (
    OperationOutcome,
)
from context.table_maintenance.application.domain.model.table_reconciliation.reconciliation_outcome import (
    ReconciliationOutcome,
)
from context.table_maintenance.application.domain.model.table_reconciliation.table_reconciliation_id import (
    TableReconciliationId,
)
from context.table_maintenance.application.domain.model.table_reconciliation.wake_reason import (
    WakeReason,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


class TableReconciliation(AggregateRoot[TableReconciliationId]):
    """Record one pass of the reconciler over a table and what it decided.

    ``policy_id``, ``policy_version`` and ``policy_target`` point at the maintenance policy the
    pass assessed with, by its ``mp-`` id, and where it is attached (``None`` for the default with
    nothing attached). The id stays after the policy is renamed or deleted. ``policy_name`` is a
    display-only copy of the policy's name when the record was written, so a record under a
    policy deleted since still reads by name; the relation is the id, never the name.
    """

    id: TableReconciliationId
    table_uuid: TableId
    reconciled_at: datetime
    wake_reasons: dict[WakeReason, int]
    dry_run: bool
    outcome: ReconciliationOutcome
    skip_reason: str | None
    operations: tuple[OperationOutcome, ...]
    policy_id: TableMaintenancePolicyId
    policy_name: TableMaintenancePolicyName
    policy_version: PositiveInt
    policy_target: PolicyTarget | None

    @model_validator(mode="after")
    def _combinations_that_cannot_happen(self) -> TableReconciliation:
        """Reject combinations of wake reasons, outcome and operations that cannot happen."""
        if not self.wake_reasons:
            raise ValueError("a reconciliation needs at least one wake reason")
        if any(count < 1 for count in self.wake_reasons.values()):
            raise ValueError("each wake reason must have been counted at least once")
        if self.outcome is ReconciliationOutcome.SKIPPED:
            if not self.skip_reason:
                raise ValueError("a skipped reconciliation needs a skip reason")
            if self.operations:
                raise ValueError("a skipped reconciliation assessed no operations")
        elif self.skip_reason is not None:
            raise ValueError("a planned reconciliation has no skip reason")
        run_ids = [op.run_id for op in self.operations if op.run_id is not None]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("each run belongs to one operation")
        return self

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
        policy_id: TableMaintenancePolicyId,
        policy_name: TableMaintenancePolicyName,
        policy_version: int,
        policy_target: PolicyTarget | None,
    ) -> TableReconciliation:
        """Record a reconciliation, keeping its operations in execution order."""
        position = {op: i for i, op in enumerate(MaintenanceOperation.ordered())}
        return cls(
            id=id,
            table_uuid=table_uuid,
            reconciled_at=reconciled_at,
            wake_reasons=dict(wake_reasons),
            dry_run=dry_run,
            outcome=outcome,
            skip_reason=skip_reason,
            operations=tuple(sorted(operations, key=lambda o: position[o.operation])),
            policy_id=policy_id,
            policy_name=policy_name,
            policy_version=policy_version,
            policy_target=policy_target,
        )
