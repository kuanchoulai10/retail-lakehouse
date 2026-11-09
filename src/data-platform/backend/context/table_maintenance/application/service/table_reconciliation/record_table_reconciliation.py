"""Define the RecordTableReconciliationService."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.shared import (
    ConditionCombine,
    MaintenanceOperation,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
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
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCase,
    RecordTableReconciliationUseCaseInput,
    RecordTableReconciliationUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_reconciliation import (
        TableReconciliationsRepo,
    )

_RETENTION = timedelta(days=30)

_RESULT_BY_VERDICT = {
    "not_needed": OperationResult.NOT_NEEDED,
    "cooling_down": OperationResult.COOLING_DOWN,
    "off": OperationResult.OFF,
    "not_checked": OperationResult.NOT_CHECKED,
}


class RecordTableReconciliationService(RecordTableReconciliationUseCase):
    """Record one reconciliation pass and purge this table's records past retention."""

    def __init__(self, reconciliations_repo: TableReconciliationsRepo) -> None:
        """Bind the repo."""
        self._reconciliations_repo = reconciliations_repo

    def execute(self, request: RecordTableReconciliationUseCaseInput) -> RecordTableReconciliationUseCaseOutput:
        """Store the reconciliation unless its id already exists, then purge old records."""
        with translate_domain_errors():
            reconciliation_id = TableReconciliationId(request.reconciliation_id)
            table_uuid = TableId(request.table_uuid)
            if self._reconciliations_repo.get(reconciliation_id) is not None:
                self._purge(table_uuid, request)
                return RecordTableReconciliationUseCaseOutput(recorded=False)
            reconciliation = TableReconciliation.record(
                id=reconciliation_id,
                table_uuid=table_uuid,
                reconciled_at=request.reconciled_at,
                wake_reasons=_wake_reasons(request.wake_reasons),
                dry_run=request.dry_run,
                outcome=_outcome(request.status),
                skip_reason=request.skip_reason,
                operations=[_operation_outcome(check, request) for check in request.checks],
                run_id=TableMaintenanceRunId(request.run_id) if request.run_id else None,
            )
            self._reconciliations_repo.create(reconciliation)
            self._purge(table_uuid, request)
        return RecordTableReconciliationUseCaseOutput(recorded=True)

    def _purge(self, table_uuid: TableId, request: RecordTableReconciliationUseCaseInput) -> None:
        self._reconciliations_repo.delete_older_than(table_uuid, request.reconciled_at - _RETENTION)


def _wake_reasons(raw: dict[str, int]) -> dict[WakeReason, int]:
    try:
        return {WakeReason(reason): count for reason, count in raw.items()}
    except ValueError as exc:
        raise ValidationError(f"unknown wake reason: {exc}") from exc


def _outcome(status: str) -> ReconciliationOutcome:
    match status:
        case "planned":
            return ReconciliationOutcome.PLANNED
        case "skip":
            return ReconciliationOutcome.SKIPPED
        case _:
            raise ValidationError(f"unknown reconciliation status: {status!r}")


def _result(verdict: str, request: RecordTableReconciliationUseCaseInput) -> OperationResult:
    if verdict != "due":
        if verdict not in _RESULT_BY_VERDICT:
            raise ValidationError(f"unknown check verdict: {verdict!r}")
        return _RESULT_BY_VERDICT[verdict]
    if request.run_id:
        return OperationResult.STARTED
    if request.run_start_failed:
        return OperationResult.START_FAILED
    if request.dry_run:
        return OperationResult.WOULD_START
    raise ValidationError("a due operation needs a run, a failed start or a dry run")


def _operation_outcome(check: dict[str, Any], request: RecordTableReconciliationUseCaseInput) -> OperationOutcome:
    try:
        verdict = check["verdict"]
        operation = MaintenanceOperation(check["operation"])
        combine = ConditionCombine(check["combine"])
        measurements = tuple(_measurement(m) for m in check.get("measurements", []))
        next_eligible_at = _instant(check.get("next_eligible_at"))
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValidationError(f"invalid check {check!r}: {exc}") from exc
    return OperationOutcome(
        operation=operation,
        result=_result(verdict, request),
        combine=combine,
        measurements=measurements,
        next_eligible_at=next_eligible_at,
    )


def _measurement(raw: dict[str, Any]) -> Measurement:
    comparison = raw.get("comparison")
    return Measurement(
        key=raw["key"],
        observed=raw["observed"],
        unit=MeasurementUnit(raw["unit"]),
        threshold=raw.get("threshold"),
        comparison=MeasurementComparison(comparison) if comparison is not None else None,
    )


def _instant(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
