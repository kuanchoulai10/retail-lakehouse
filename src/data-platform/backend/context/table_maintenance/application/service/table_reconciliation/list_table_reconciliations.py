"""Define the ListTableReconciliationsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCase,
    ListTableReconciliationsUseCaseInput,
    ListTableReconciliationsUseCaseOutput,
    ListTableReconciliationsUseCaseOutputItem,
    ListTableReconciliationsUseCaseOutputMeasurement,
    ListTableReconciliationsUseCaseOutputOperation,
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
        return ListTableReconciliationsUseCaseOutput(items=[_item(r) for r in found])


def _item(reconciliation: TableReconciliation) -> ListTableReconciliationsUseCaseOutputItem:
    return ListTableReconciliationsUseCaseOutputItem(
        reconciliation_id=reconciliation.id.value,
        table_uuid=reconciliation.table_uuid.value,
        reconciled_at=reconciliation.reconciled_at,
        wake_reasons={reason.value: count for reason, count in reconciliation.wake_reasons.items()},
        dry_run=reconciliation.dry_run,
        outcome=reconciliation.outcome.value,
        skip_reason=reconciliation.skip_reason,
        operations=[_operation(op) for op in reconciliation.operations],
        run_id=reconciliation.run_id.value if reconciliation.run_id else None,
    )


def _operation(outcome: OperationOutcome) -> ListTableReconciliationsUseCaseOutputOperation:
    return ListTableReconciliationsUseCaseOutputOperation(
        operation=outcome.operation.value,
        result=outcome.result.value,
        combine=outcome.combine.value,
        measurements=[_measurement(m) for m in outcome.measurements],
        next_eligible_at=outcome.next_eligible_at,
    )


def _measurement(measurement: Measurement) -> ListTableReconciliationsUseCaseOutputMeasurement:
    return ListTableReconciliationsUseCaseOutputMeasurement(
        key=measurement.key,
        observed=measurement.observed,
        unit=measurement.unit.value,
        threshold=measurement.threshold,
        comparison=measurement.comparison.value if measurement.comparison else None,
        met=measurement.met,
    )
