"""Define the MaintenanceRun aggregate root."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.invalid_run_transition import (
    InvalidRunTransition,
)
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.model.maintenance_run.operation_run import OperationRun
from application.domain.model.maintenance_run.operation_run_status import (
    OperationRunStatus,
)
from application.domain.model.maintenance_run.run_status import RunStatus
from application.domain.model.maintenance_run.trigger_type import TriggerType
from application.domain.model.managed_table.table_uuid import TableUuid
from base.aggregate_root import AggregateRoot

_TERMINAL = frozenset(
    {
        OperationRunStatus.SUCCEEDED,
        OperationRunStatus.FAILED,
        OperationRunStatus.SKIPPED,
    }
)


@dataclass(eq=False)
class MaintenanceRun(AggregateRoot[MaintenanceRunId]):
    """Track one execution of maintenance operations against a table."""

    id: MaintenanceRunId
    table_uuid: TableUuid
    trigger: TriggerType
    operations: tuple[OperationRun, ...]
    created_at: datetime
    finished_at: datetime | None = None

    @classmethod
    def create(
        cls,
        id: MaintenanceRunId,  # noqa: A002
        table_uuid: TableUuid,
        trigger: TriggerType,
        operations: Sequence[MaintenanceOperation],
        now: datetime,
    ) -> MaintenanceRun:
        """Create a run with the given operations in canonical order, all pending."""
        requested = set(operations)
        if not requested:
            msg = "a maintenance run needs at least one operation"
            raise InvalidRunTransition(msg)
        return cls(
            id=id,
            table_uuid=table_uuid,
            trigger=trigger,
            operations=tuple(
                OperationRun(operation=op)
                for op in MaintenanceOperation.ordered()
                if op in requested
            ),
            created_at=now,
        )

    @property
    def status(self) -> RunStatus:
        """Derive the run status from its operations."""
        statuses = [op.status for op in self.operations]
        if all(s is OperationRunStatus.PENDING for s in statuses):
            return RunStatus.PENDING
        if any(s not in _TERMINAL for s in statuses):
            return RunStatus.RUNNING
        counted = [s for s in statuses if s is not OperationRunStatus.SKIPPED]
        if all(s is OperationRunStatus.SUCCEEDED for s in counted):
            return RunStatus.SUCCEEDED
        if all(s is OperationRunStatus.FAILED for s in counted):
            return RunStatus.FAILED
        return RunStatus.PARTIALLY_FAILED

    def start_attempt(
        self,
        operation: MaintenanceOperation,
        attempt: int,
        spark_application: str,
        now: datetime,
    ) -> None:
        """Mark an attempt of an operation as running."""
        current = self._get(operation)
        if (
            attempt == current.attempts
            and current.status is OperationRunStatus.RUNNING
            and current.spark_application == spark_application
        ):
            return
        startable = current.status in (
            OperationRunStatus.PENDING,
            OperationRunStatus.FAILED,
        )
        if attempt != current.attempts + 1 or not startable:
            msg = (
                f"cannot start attempt {attempt} of {operation} "
                f"(status {current.status}, attempts {current.attempts})"
            )
            raise InvalidRunTransition(msg)
        self._replace(
            replace(
                current,
                status=OperationRunStatus.RUNNING,
                attempts=attempt,
                spark_application=spark_application,
                started_at=now,
                finished_at=None,
                error=None,
                metrics={},
            ),
            now,
        )

    def succeed(
        self,
        operation: MaintenanceOperation,
        attempt: int,
        metrics: dict[str, int],
        now: datetime,
    ) -> None:
        """Record that an attempt succeeded."""
        self._finish(
            operation,
            attempt,
            OperationRunStatus.SUCCEEDED,
            now,
            metrics=dict(metrics),
            error=None,
        )

    def fail(
        self,
        operation: MaintenanceOperation,
        attempt: int,
        error: str,
        now: datetime,
    ) -> None:
        """Record that an attempt failed."""
        self._finish(
            operation, attempt, OperationRunStatus.FAILED, now, metrics={}, error=error
        )

    def skip(self, operation: MaintenanceOperation, reason: str, now: datetime) -> None:
        """Skip a pending operation."""
        current = self._get(operation)
        if current.status is not OperationRunStatus.PENDING:
            msg = f"cannot skip {operation} in status {current.status}"
            raise InvalidRunTransition(msg)
        self._replace(
            replace(
                current,
                status=OperationRunStatus.SKIPPED,
                error=reason,
                finished_at=now,
            ),
            now,
        )

    def _finish(
        self,
        operation: MaintenanceOperation,
        attempt: int,
        outcome: OperationRunStatus,
        now: datetime,
        *,
        metrics: dict[str, int],
        error: str | None,
    ) -> None:
        current = self._get(operation)
        if attempt < current.attempts:
            return
        if attempt > current.attempts or current.attempts == 0:
            msg = f"attempt {attempt} of {operation} was never started"
            raise InvalidRunTransition(msg)
        if current.status is outcome:
            return
        if current.status is not OperationRunStatus.RUNNING:
            msg = f"cannot mark {operation} {outcome} from status {current.status}"
            raise InvalidRunTransition(msg)
        self._replace(
            replace(
                current,
                status=outcome,
                finished_at=now,
                metrics=metrics,
                error=error,
            ),
            now,
        )

    def _get(self, operation: MaintenanceOperation) -> OperationRun:
        for run in self.operations:
            if run.operation == operation:
                return run
        msg = f"operation {operation} is not part of run {self.id}"
        raise InvalidRunTransition(msg)

    def _replace(self, updated: OperationRun, now: datetime) -> None:
        self.operations = tuple(
            updated if run.operation == updated.operation else run
            for run in self.operations
        )
        if all(run.status in _TERMINAL for run in self.operations):
            self.finished_at = now
        else:
            self.finished_at = None
