"""Define the GetTableReconciliationUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetTableReconciliationUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to get one reconciliation.

    ``policy_id`` is the ``mp-`` id of the policy the reconciliation used and ``policy_name``
    that policy's current name, or, when ``policy_deleted`` says the policy has been deleted
    since, the name it had when the reconciliation was recorded.
    """

    class Measurement(UseCaseOutput):
        """One measurement of an operation; threshold, comparison and met are None for context."""

        key: str
        observed: int
        unit: str
        threshold: int | None
        comparison: str | None
        met: bool | None

    class Operation(UseCaseOutput):
        """What a reconciliation measured and decided for one operation; ``run_id`` is the run it started."""

        operation: str
        result: str
        measurements: tuple[GetTableReconciliationUseCaseOutput.Measurement, ...]
        next_eligible_at: datetime | None
        run_id: str | None

    class PolicyTarget(UseCaseOutput):
        """Where the policy a reconciliation used was attached."""

        type: str
        path: tuple[str, ...]

    reconciliation_id: str
    table_uuid: str
    reconciled_at: datetime
    wake_reasons: dict[str, int]
    dry_run: bool
    outcome: str
    skip_reason: str | None
    operations: tuple[GetTableReconciliationUseCaseOutput.Operation, ...]
    policy_id: str
    policy_name: str
    policy_deleted: bool
    policy_version: int
    policy_target: GetTableReconciliationUseCaseOutput.PolicyTarget | None
