"""Define the TableMaintenanceRun aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run.failure_class import (
    FailureClass,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.invalid_run_transition import (
    InvalidRunTransition,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.next_step import (
    NextStep,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.operation_attempt import (
    OperationAttempt,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.operation_run import (
    OperationRun,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.operation_run_status import (
    OperationRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.table_maintenance_run_id import (
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.trigger_type import (
    TriggerType,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.table_maintenance_run.next_attempt import (
        NextAttempt,
    )

_TERMINAL = frozenset(
    {
        OperationRunStatus.SUCCEEDED,
        OperationRunStatus.FAILED,
        OperationRunStatus.SKIPPED,
    }
)


class TableMaintenanceRun(AggregateRoot[TableMaintenanceRunId]):
    """Track one execution of maintenance operations against a table."""

    id: TableMaintenanceRunId
    table_uuid: TableId
    trigger: TriggerType
    operations: tuple[OperationRun, ...]
    created_at: datetime
    execution_ref: str
    finished_at: datetime | None = None
    priority: TablePriority = TablePriority.P3

    @classmethod
    def create(
        cls,
        id: TableMaintenanceRunId,  # noqa: A002
        table_uuid: TableId,
        trigger: TriggerType,
        operations: Sequence[MaintenanceOperation],
        now: datetime,
        *,
        execution_ref: str,
        priority: TablePriority = TablePriority.P3,
    ) -> TableMaintenanceRun:
        """Create a run with the given operations in canonical order, all pending.

        ``execution_ref`` names the execution that runs it, so a result
        that only carries the run id can still be routed to that execution.
        ``priority`` is the priority the run was started with.
        """
        if not execution_ref:
            msg = "a maintenance run needs the execution reference that runs it"
            raise ValueError(msg)
        requested = set(operations)
        if not requested:
            msg = "a maintenance run needs at least one operation"
            raise InvalidRunTransition(msg)
        return cls(
            id=id,
            table_uuid=table_uuid,
            trigger=trigger,
            operations=tuple(OperationRun(operation=op) for op in MaintenanceOperation.ordered() if op in requested),
            created_at=now,
            execution_ref=execution_ref,
            priority=priority,
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
        job_name: str | None,
        now: datetime,
        *,
        size: ComputeSize | None = None,
    ) -> None:
        """Mark an attempt of an operation as running at ``size`` and add it to the attempt history.

        Starting the attempt that is already running is a no-op, except that a
        given ``job_name`` is attached when none is recorded yet.
        """
        current = self._get(operation)
        if attempt == current.attempts and current.status is OperationRunStatus.RUNNING:
            if job_name is not None:
                self.attach_job_name(operation, attempt, job_name)
            return
        self._require_startable(current, operation, attempt)
        self._replace(
            current.with_changes(
                status=OperationRunStatus.RUNNING,
                attempts=attempt,
                job_name=job_name,
                started_at=now,
                finished_at=None,
                error=None,
                metrics={},
                attempt_history=(
                    *current.attempt_history,
                    OperationAttempt(attempt=attempt, size=size, status=OperationRunStatus.RUNNING, started_at=now),
                ),
            ),
            now,
        )

    def attempt_record(self, operation: MaintenanceOperation, attempt: int) -> OperationAttempt | None:
        """Return the history entry of one attempt of an operation, or None when it has none."""
        return next((a for a in self._get(operation).attempt_history if a.attempt == attempt), None)

    def attach_job_name(self, operation: MaintenanceOperation, attempt: int, job_name: str) -> None:
        """Record the job of the running attempt; repeating the same name is a no-op."""
        current = self._get(operation)
        if attempt != current.attempts or current.status is not OperationRunStatus.RUNNING:
            msg = (
                f"cannot attach a job to attempt {attempt} of {operation} "
                f"(status {current.status}, attempts {current.attempts})"
            )
            raise InvalidRunTransition(msg)
        if current.job_name == job_name:
            return
        if current.job_name is not None:
            msg = f"attempt {attempt} of {operation} already has job {current.job_name}"
            raise InvalidRunTransition(msg)
        self.operations = tuple(
            run.with_changes(job_name=job_name) if run.operation == operation else run for run in self.operations
        )

    def succeed(
        self,
        operation: MaintenanceOperation,
        attempt: int,
        metrics: dict[str, int],
        now: datetime,
        *,
        event_log_finished: bool | None = None,
    ) -> None:
        """Record that an attempt succeeded; nothing follows it."""
        self._finish(
            operation,
            attempt,
            OperationRunStatus.SUCCEEDED,
            now,
            metrics=dict(metrics),
            error=None,
            failure_class=None,
            event_log_finished=event_log_finished,
            next_step=NextStep.DONE,
            next_size=None,
        )

    def fail(
        self,
        operation: MaintenanceOperation,
        attempt: int,
        error: str,
        now: datetime,
        *,
        failure_class: FailureClass = FailureClass.OTHER,
        event_log_finished: bool | None = None,
        next_attempt: NextAttempt | None = None,
    ) -> None:
        """Record that an attempt failed, why, and what follows it when that is decided."""
        self._finish(
            operation,
            attempt,
            OperationRunStatus.FAILED,
            now,
            metrics={},
            error=error,
            failure_class=failure_class,
            event_log_finished=event_log_finished,
            next_step=next_attempt.step if next_attempt else None,
            next_size=next_attempt.size if next_attempt else None,
        )

    def skip(self, operation: MaintenanceOperation, reason: str, now: datetime) -> None:
        """Skip a pending operation."""
        current = self._get(operation)
        if current.status is not OperationRunStatus.PENDING:
            msg = f"cannot skip {operation} in status {current.status}"
            raise InvalidRunTransition(msg)
        self._replace(
            current.with_changes(
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
        status: OperationRunStatus,
        now: datetime,
        *,
        metrics: dict[str, int],
        error: str | None,
        failure_class: FailureClass | None,
        event_log_finished: bool | None,
        next_step: NextStep | None,
        next_size: ComputeSize | None,
    ) -> None:
        current = self._get(operation)
        if attempt < current.attempts:
            return
        if attempt > current.attempts or current.attempts == 0:
            msg = f"attempt {attempt} of {operation} was never started"
            raise InvalidRunTransition(msg)
        if current.status is status:
            return
        if current.status is not OperationRunStatus.RUNNING:
            msg = f"cannot mark {operation} {status} from status {current.status}"
            raise InvalidRunTransition(msg)
        self._replace(
            current.with_changes(
                status=status,
                finished_at=now,
                metrics=metrics,
                error=error,
                attempt_history=self._finished_history(
                    current,
                    attempt,
                    status,
                    now,
                    failure_class=failure_class,
                    error=error,
                    event_log_finished=event_log_finished,
                    next_step=next_step,
                    next_size=next_size,
                ),
            ),
            now,
        )

    @staticmethod
    def _finished_history(
        current: OperationRun,
        attempt: int,
        status: OperationRunStatus,
        now: datetime,
        **outcome: object,
    ) -> tuple[OperationAttempt, ...]:
        """Return the history with the finished attempt's outcome, adding an entry it lacks.

        An attempt started before attempt history existed has no entry; it gets one with no size,
        started when its operation's latest attempt started.
        """
        history = current.attempt_history
        if not any(a.attempt == attempt for a in history):
            started_at = current.started_at or now
            history = (*history, OperationAttempt(attempt=attempt, size=None, status=status, started_at=started_at))
        return tuple(
            entry.with_changes(
                status=status,
                finished_at=now,
                **outcome,
            )
            if entry.attempt == attempt
            else entry
            for entry in history
        )

    @staticmethod
    def _require_startable(current: OperationRun, operation: MaintenanceOperation, attempt: int) -> None:
        startable = current.status in (
            OperationRunStatus.PENDING,
            OperationRunStatus.FAILED,
        )
        if attempt != current.attempts + 1 or not startable:
            msg = (
                f"cannot start attempt {attempt} of {operation} (status {current.status}, attempts {current.attempts})"
            )
            raise InvalidRunTransition(msg)

    def _get(self, operation: MaintenanceOperation) -> OperationRun:
        for run in self.operations:
            if run.operation == operation:
                return run
        msg = f"operation {operation} is not part of run {self.id}"
        raise InvalidRunTransition(msg)

    def _replace(self, updated: OperationRun, now: datetime) -> None:
        operations = tuple(updated if run.operation == updated.operation else run for run in self.operations)
        finished_at = now if all(run.status in _TERMINAL for run in operations) else None
        self._assign_together(operations=operations, finished_at=finished_at)
