"""Define the TableMaintenanceRun aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from base import AggregateRoot, ReadOnlyMapping
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    SpecFilter,
    TableId,
    TableMaintenanceRunId,
    TablePriority,
)
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
from context.table_maintenance.application.domain.model.table_maintenance_run.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.trigger_type import (
    TriggerType,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from context.table_maintenance.application.domain.model.table_maintenance_run.next_attempt import (
        NextAttempt,
    )

_IN_FLIGHT = frozenset({RunStatus.QUEUED, RunStatus.RUNNING})

_TERMINAL = frozenset({RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.SKIPPED})

_NEVER_STARTED = frozenset({RunStatus.PENDING, RunStatus.SKIPPED})


def _misplaced_filters(operation: MaintenanceOperation, filters: Sequence[SpecFilter]) -> str | None:
    """Return why a run of ``operation`` cannot hold ``filters``, or None when it can."""
    if filters and operation is not MaintenanceOperation.REWRITE_DATA_FILES:
        return f"a {operation} run cannot hold filters: only a rewrite_data_files run can"
    return None


class TableMaintenanceRun(AggregateRoot[TableMaintenanceRunId]):
    """Track one maintenance operation against a table, its attempts as its timeline.

    ``status`` is the run's one status: pending until the first attempt is submitted, then the status of
    its latest attempt, or skipped when it never started. A run whose attempt failed and will be retried
    reads failed, with a finish time, until the next attempt is submitted. ``filters`` holds the where
    clauses, one per partition spec, every attempt of a compaction passes to ``rewrite_data_files``; empty
    means the whole table. ``procedure_args`` holds the arguments the procedure is called with, and
    ``metrics`` the numbers it returned. ``error`` is the latest failure's error and ``skip_reason`` why a
    skipped run never started.
    """

    id: TableMaintenanceRunId
    table_uuid: TableId
    trigger: TriggerType
    operation: MaintenanceOperation
    created_at: datetime
    execution_ref: str
    priority: TablePriority = TablePriority.P3
    status: RunStatus = RunStatus.PENDING
    filters: tuple[SpecFilter, ...] = ()
    procedure_args: ReadOnlyMapping[str, Any] = Field(default_factory=dict)
    metrics: ReadOnlyMapping[str, Any] = Field(default_factory=dict)
    error: str | None = None
    skip_reason: str | None = None
    finished_at: datetime | None = None
    attempts: tuple[OperationAttempt, ...] = ()

    @model_validator(mode="after")
    def _attempts_count_up_from_one(self) -> TableMaintenanceRun:
        numbers = [entry.attempt for entry in self.attempts]
        if numbers and numbers[0] != 1:
            msg = f"the attempts of run {self.id} must start at 1: {numbers}"
            raise ValueError(msg)
        if any(later <= earlier for earlier, later in zip(numbers, numbers[1:], strict=False)):
            msg = f"the attempt numbers of run {self.id} must increase: {numbers}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _only_a_compaction_holds_filters(self) -> TableMaintenanceRun:
        if msg := _misplaced_filters(self.operation, self.filters):
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _a_skip_reason_only_when_skipped(self) -> TableMaintenanceRun:
        if (self.skip_reason is not None) != (self.status is RunStatus.SKIPPED):
            msg = f"a run has a skip reason exactly when it is skipped: run {self.id} is {self.status}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _a_finish_time_only_when_terminal(self) -> TableMaintenanceRun:
        if (self.finished_at is not None) != (self.status in _TERMINAL):
            msg = (
                f"a run has a finish time exactly when it is succeeded, failed or skipped: "
                f"run {self.id} is {self.status}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _status_is_the_latest_attempts(self) -> TableMaintenanceRun:
        if not self.attempts:
            if self.status not in _NEVER_STARTED:
                msg = f"run {self.id} has no attempt, so it is pending or skipped, not {self.status}"
                raise ValueError(msg)
        elif self.status is not self.attempts[-1].status:
            latest = self.attempts[-1]
            msg = (
                f"a run reads its latest attempt's status: run {self.id} is {self.status}, "
                f"attempt {latest.attempt} is {latest.status}"
            )
            raise ValueError(msg)
        return self

    @classmethod
    def create(
        cls,
        id: TableMaintenanceRunId,  # noqa: A002
        table_uuid: TableId,
        trigger: TriggerType,
        operation: MaintenanceOperation,
        now: datetime,
        *,
        execution_ref: str,
        priority: TablePriority = TablePriority.P3,
        filters: Sequence[SpecFilter] = (),
        procedure_args: Mapping[str, Any] | None = None,
    ) -> TableMaintenanceRun:
        """Create a pending run of one operation.

        ``execution_ref`` names the execution that runs it, so a result
        that only carries the run id can still be routed to that execution.
        ``priority`` is the priority the run was started with. ``filters`` holds the where clauses
        every attempt is submitted with; only a ``rewrite_data_files`` run may hold any.
        ``procedure_args`` holds the arguments the procedure is called with.
        """
        if not execution_ref:
            msg = "a maintenance run needs the execution reference that runs it"
            raise ValueError(msg)
        if msg := _misplaced_filters(operation, filters):
            raise InvalidRunTransition(msg)
        return cls(
            id=id,
            table_uuid=table_uuid,
            trigger=trigger,
            operation=operation,
            created_at=now,
            execution_ref=execution_ref,
            priority=priority,
            filters=tuple(filters),
            procedure_args=dict(procedure_args or {}),
        )

    @property
    def started_at(self) -> datetime | None:
        """Return when the run's first attempt was submitted, or None before it was."""
        return self.attempts[0].started_at if self.attempts else None

    @property
    def current_attempt(self) -> int:
        """Return the number of the run's latest attempt, or 0 before the first was submitted."""
        return self.attempts[-1].attempt if self.attempts else 0

    def start_attempt(
        self,
        attempt: int,
        job_name: str | None,
        now: datetime,
        *,
        size: ComputeSize,
    ) -> None:
        """Mark an attempt as queued at ``size`` with its job and add it to the attempts.

        The attempt stays queued until ``record_attempt_running`` says its driver runs. Starting the
        attempt that is already queued or running is a no-op, except that a given ``job_name`` is
        attached when none is recorded yet. A new attempt clears the previous attempt's outcome from the
        run.
        """
        if attempt == self.current_attempt and self.status in _IN_FLIGHT:
            if job_name is not None:
                self.attach_job_name(attempt, job_name)
            return
        self._require_startable(attempt)
        self._assign_together(
            status=RunStatus.QUEUED,
            finished_at=None,
            error=None,
            metrics={},
            attempts=(
                *self.attempts,
                OperationAttempt(
                    attempt=attempt, size=size, status=RunStatus.QUEUED, started_at=now, job_name=job_name
                ),
            ),
        )

    def raise_priority(self, priority: TablePriority) -> bool:
        """Raise the run to ``priority`` and tell whether it was raised.

        Only a priority that outranks the run's raises it, and only while the run has not ended; an equal
        or lower one, or an ended run, changes nothing. A run ends when it succeeded, was skipped, or failed
        with no retry to follow; a run waiting out the backoff before its retry still takes a raise, so the
        retry submits at the new priority.
        """
        if self._ended or not priority.outranks(self.priority):
            return False
        self.priority = priority
        return True

    def attempt_record(self, attempt: int) -> OperationAttempt | None:
        """Return one attempt of the run, or None when it has none by that number."""
        return next((a for a in self.attempts if a.attempt == attempt), None)

    def record_attempt_running(self, attempt: int, started_running_at: datetime, now: datetime) -> None:
        """Record that the driver of an attempt started running at ``started_running_at``.

        The time is clamped into the attempt's submit time and ``now``. A queued attempt becomes
        running; a running one is left alone; a finished attempt that has no running time only gets
        it, within its own span, and keeps its status. A report for an earlier attempt is ignored.
        """
        record = self._current_record(attempt)
        if record is None or record.status is RunStatus.RUNNING:
            return
        if record.finished:
            if record.started_running_at is None and record.finished_at is not None:
                self._assign_together(
                    attempts=self._with_attempt(
                        attempt,
                        started_running_at=self._running_time(record, started_running_at, record.finished_at),
                    )
                )
            return
        self._assign_together(
            status=RunStatus.RUNNING,
            attempts=self._with_attempt(
                attempt,
                status=RunStatus.RUNNING,
                started_running_at=self._clamp(started_running_at, record.started_at, now),
            ),
        )

    def attach_job_name(self, attempt: int, job_name: str) -> None:
        """Record the job of the queued or running attempt; repeating the same name is a no-op."""
        if attempt != self.current_attempt or self.status not in _IN_FLIGHT:
            msg = (
                f"cannot attach a job to attempt {attempt} of run {self.id} "
                f"(status {self.status}, attempts {self.current_attempt})"
            )
            raise InvalidRunTransition(msg)
        current = self.attempts[-1].job_name
        if current == job_name:
            return
        if current is not None:
            msg = f"attempt {attempt} of run {self.id} already has job {current}"
            raise InvalidRunTransition(msg)
        self._assign_together(attempts=self._with_attempt(attempt, job_name=job_name))

    def succeed(
        self,
        attempt: int,
        metrics: Mapping[str, Any],
        now: datetime,
        *,
        started_running_at: datetime | None = None,
        event_log_finished: bool | None = None,
    ) -> None:
        """Record that an attempt succeeded, with the numbers the procedure returned; nothing follows it.

        ``started_running_at`` fills the attempt's running time when it has none.
        """
        self._finish(
            attempt,
            RunStatus.SUCCEEDED,
            now,
            started_running_at=started_running_at,
            metrics=dict(metrics),
            error=None,
            failure_class=None,
            event_log_finished=event_log_finished,
            next_step=NextStep.DONE,
            next_size=None,
        )

    def fail(
        self,
        attempt: int,
        error: str,
        now: datetime,
        *,
        failure_class: FailureClass = FailureClass.OTHER,
        started_running_at: datetime | None = None,
        event_log_finished: bool | None = None,
        next_attempt: NextAttempt | None = None,
    ) -> None:
        """Record that an attempt failed, why, and what follows it when that is decided.

        The run reads failed, with a finish time, even when a retry follows; the retry's
        ``start_attempt`` queues it again. ``started_running_at`` fills the attempt's running time when
        it has none.
        """
        self._finish(
            attempt,
            RunStatus.FAILED,
            now,
            started_running_at=started_running_at,
            metrics={},
            error=error,
            failure_class=failure_class,
            event_log_finished=event_log_finished,
            next_step=next_attempt.step if next_attempt else None,
            next_size=next_attempt.size if next_attempt else None,
        )

    def skip(self, reason: str, now: datetime) -> None:
        """Skip a run that never started, saying why."""
        if self.status is not RunStatus.PENDING:
            msg = f"cannot skip run {self.id} in status {self.status}"
            raise InvalidRunTransition(msg)
        self._assign_together(status=RunStatus.SKIPPED, skip_reason=reason, finished_at=now)

    @property
    def _ended(self) -> bool:
        """Return whether nothing more happens to the run: succeeded, skipped, or failed with no retry."""
        if self.status is RunStatus.FAILED:
            next_step = self.attempts[-1].next_step if self.attempts else None
            return next_step is None or not next_step.retries
        return self.status in _TERMINAL

    def _current_record(self, attempt: int) -> OperationAttempt | None:
        """Return the current attempt when ``attempt`` is it, None for an earlier one; refuse a later one."""
        if attempt < self.current_attempt:
            return None
        if attempt > self.current_attempt or not self.attempts:
            msg = f"attempt {attempt} of run {self.id} was never started"
            raise InvalidRunTransition(msg)
        return self.attempts[-1]

    def _finish(
        self,
        attempt: int,
        status: RunStatus,
        now: datetime,
        *,
        started_running_at: datetime | None,
        metrics: dict[str, Any],
        error: str | None,
        **outcome: object,
    ) -> None:
        record = self._current_record(attempt)
        if record is None or self.status is status:
            return
        if self.status not in _IN_FLIGHT:
            msg = f"cannot mark run {self.id} {status} from status {self.status}"
            raise InvalidRunTransition(msg)
        self._assign_together(
            status=status,
            finished_at=now,
            metrics=metrics,
            error=error,
            attempts=self._with_attempt(
                attempt,
                status=status,
                finished_at=now,
                started_running_at=self._running_time(record, started_running_at, now),
                error=error,
                **outcome,
            ),
        )

    def _with_attempt(self, attempt: int, **changes: object) -> tuple[OperationAttempt, ...]:
        return tuple(entry.with_changes(**changes) if entry.attempt == attempt else entry for entry in self.attempts)

    @staticmethod
    def _running_time(entry: OperationAttempt, reported: datetime | None, upper: datetime) -> datetime | None:
        """Return the attempt's running time: the one it has, else ``reported`` clamped into its span."""
        if entry.started_running_at is not None or reported is None:
            return entry.started_running_at
        return TableMaintenanceRun._clamp(reported, entry.started_at, upper)

    @staticmethod
    def _clamp(value: datetime, lower: datetime, upper: datetime) -> datetime:
        """Return ``value`` within ``lower`` and ``upper``, and never below ``lower`` when ``upper`` is earlier."""
        return min(max(value, lower), max(upper, lower))

    def _require_startable(self, attempt: int) -> None:
        startable = self.status in (RunStatus.PENDING, RunStatus.FAILED)
        if attempt != self.current_attempt + 1 or not startable:
            msg = (
                f"cannot start attempt {attempt} of run {self.id} "
                f"(status {self.status}, attempts {self.current_attempt})"
            )
            raise InvalidRunTransition(msg)
