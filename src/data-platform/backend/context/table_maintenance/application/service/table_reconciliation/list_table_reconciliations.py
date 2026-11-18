"""Define the ListTableReconciliationsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCase,
    ListTableReconciliationsUseCaseInput,
    ListTableReconciliationsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import Measurement
    from context.table_maintenance.application.domain.model.table_reconciliation import (
        OperationOutcome,
        TableReconciliation,
    )
    from context.table_maintenance.application.port.outbound.table_reconciliation import (
        TableReconciliationsRepo,
    )


class ListTableReconciliationsService(ListTableReconciliationsUseCase):
    """List the reconciliations of a table, newest first."""

    def __init__(self, reconciliations_repo: TableReconciliationsRepo) -> None:
        """Bind the repo."""
        self._reconciliations_repo = reconciliations_repo

    def execute(self, request: ListTableReconciliationsUseCaseInput) -> ListTableReconciliationsUseCaseOutput:
        """Return up to ``limit`` reconciliations strictly before ``before``."""
        found = self._reconciliations_repo.list_by_table(
            TableId(request.table_uuid), before=request.before, limit=request.limit
        )
        return ListTableReconciliationsUseCaseOutput(items=tuple(_item(r) for r in found))


def _item(reconciliation: TableReconciliation) -> ListTableReconciliationsUseCaseOutput.TableReconciliation:
    return ListTableReconciliationsUseCaseOutput.TableReconciliation(
        reconciliation_id=reconciliation.id.value,
        table_uuid=reconciliation.table_uuid.value,
        reconciled_at=reconciliation.reconciled_at,
        wake_reasons={reason.value: count for reason, count in reconciliation.wake_reasons.items()},
        dry_run=reconciliation.dry_run,
        outcome=reconciliation.outcome.value,
        skip_reason=reconciliation.skip_reason,
        operations=tuple(_operation(op) for op in reconciliation.operations),
        run_id=reconciliation.run_id.value if reconciliation.run_id else None,
        policy_name=reconciliation.policy_name,
        policy_version=reconciliation.policy_version,
        policy_target=_policy_target(reconciliation),
    )


def _policy_target(
    reconciliation: TableReconciliation,
) -> ListTableReconciliationsUseCaseOutput.PolicyTarget | None:
    target = reconciliation.policy_target
    if target is None:
        return None
    return ListTableReconciliationsUseCaseOutput.PolicyTarget(type=target.type.value, path=tuple(target.path))


def _operation(outcome: OperationOutcome) -> ListTableReconciliationsUseCaseOutput.Operation:
    return ListTableReconciliationsUseCaseOutput.Operation(
        operation=outcome.operation.value,
        result=outcome.result.value,
        measurements=tuple(_measurement(m) for m in outcome.measurements),
        next_eligible_at=outcome.next_eligible_at,
    )


def _measurement(measurement: Measurement) -> ListTableReconciliationsUseCaseOutput.Measurement:
    return ListTableReconciliationsUseCaseOutput.Measurement(
        key=measurement.key,
        observed=measurement.observed,
        unit=measurement.unit.value,
        threshold=measurement.threshold,
        comparison=measurement.comparison.value if measurement.comparison else None,
        met=measurement.met,
    )
