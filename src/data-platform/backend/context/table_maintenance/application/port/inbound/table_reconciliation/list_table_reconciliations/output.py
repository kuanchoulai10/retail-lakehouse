"""Define the ListTableReconciliationsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListTableReconciliationsUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to list the reconciliations of a table."""

    class Measurement(UseCaseOutput):
        """One measurement of an operation; threshold, comparison and met are None for context."""

        key: str
        observed: int
        unit: str
        threshold: int | None
        comparison: str | None
        met: bool | None

    class Operation(UseCaseOutput):
        """What a reconciliation measured and decided for one operation."""

        operation: str
        result: str
        measurements: tuple[ListTableReconciliationsUseCaseOutput.Measurement, ...]
        next_eligible_at: datetime | None

    class PolicyTarget(UseCaseOutput):
        """Where the policy a reconciliation used was attached."""

        type: str
        path: tuple[str, ...]

    class TableReconciliation(UseCaseOutput):
        """One reconciliation of the listing."""

        reconciliation_id: str
        table_uuid: str
        reconciled_at: datetime
        wake_reasons: dict[str, int]
        dry_run: bool
        outcome: str
        skip_reason: str | None
        operations: tuple[ListTableReconciliationsUseCaseOutput.Operation, ...]
        run_id: str | None
        policy_name: str
        policy_version: int
        policy_target: ListTableReconciliationsUseCaseOutput.PolicyTarget | None

    items: tuple[TableReconciliation, ...]
