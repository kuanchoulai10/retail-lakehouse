"""Define the OperationResultSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance.attempt_ending import (
    MaintenanceAttemptEnding,
)


@dataclass(frozen=True)
class OperationResultSignal:
    """Payload of the operation_result signal sent to a table maintenance workflow.

    A result Spark sends ended its attempt by reporting it (``ended_by`` ``result``); the workflow
    builds results of its own for the other endings, and marks one whose job may still be running.
    """

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict
    error: str | None
    ended_by: str = MaintenanceAttemptEnding.RESULT
    still_running: bool = False
