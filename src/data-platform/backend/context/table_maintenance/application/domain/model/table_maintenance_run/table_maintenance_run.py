"""Define the TableMaintenanceRun aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from base import AggregateRoot, ReadOnlyMapping
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TableId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.attempt.attempt_status import (
    AttemptStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.attempt.failure_class import (
    FailureClass,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.attempt.next_step import (
    NextStep,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.attempt.operation_attempt import (
    OperationAttempt,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.job_content.maintenance_job_content import (  # noqa: E501
    MaintenanceJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.invalid_run_transition import (
    InvalidRunTransition,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.pending_run_status import (
    PendingRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_field import (
    RunStatusField,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.trigger_type import (
    TriggerType,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from context.table_maintenance.application.domain.model.table_maintenance_run.attempt.next_attempt import (
        NextAttempt,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
        RunStatus,
    )


def _misplaced_content(operation: MaintenanceOperation, content: MaintenanceJobContent) -> str | None:
    """Return why a run of ``operation`` cannot hold ``content``, or None when it can."""
    if content.operation != operation:
        return f"a {operation} run cannot hold {content.operation} content"
    return None


def _statuses_agreeing_with(latest: OperationAttempt | None) -> frozenset[RunStatusName]:
    """Return the run statuses that agree with the run's latest attempt, or with its having none.

    A run with no attempt is pending, skipped or cancelled. A failed attempt with a retry to follow leaves the
    run waiting to retry, or cancelled when it was cancelled while it waited; a cancelled attempt leaves it
    cancelled. A run stored before those two statuses existed reads failed for either, so failed agrees with
    every failed attempt. Any other attempt gives the run its own status.
    """
    if latest is None:
        return frozenset({RunStatusName.PENDING, RunStatusName.SKIPPED, RunStatusName.CANCELLED})
    if latest.status is not AttemptStatus.FAILED:
        return frozenset({RunStatusName(latest.status.value)})
    if latest.next_step is not None and latest.next_step.retries:
        return frozenset({RunStatusName.RETRY_WAITING, RunStatusName.CANCELLED, RunStatusName.FAILED})
    if latest.next_step is NextStep.CANCELLED:
        return frozenset({RunStatusName.CANCELLED, RunStatusName.FAILED})
    return frozenset({RunStatusName.FAILED})


class TableMaintenanceRun(AggregateRoot[TableMaintenanceRunId]):
    """Track one maintenance operation against a table, its attempts as its timeline.

    ``status`` is the run's one status, a ``RunStatus`` that says which changes it allows and what each
    leads to; every change of status asks it first. A run is pending until its first attempt is submitted,
    then queued and running with its attempt. A failed attempt with a retry to follow leaves the run
    waiting to retry, with no finish time, until the next attempt is submitted; one with none fails it.
    The run ends succeeded, failed, cancelled, or skipped when it never started, and has a finish time
    exactly when it has ended. ``content`` is what every
    attempt does: the settings of its operation and, for a compaction, the partitions it rewrites (none
    means the whole table). ``metrics`` holds the numbers the job returned. ``error`` is the latest
    failure's error and ``skip_reason`` why a skipped run never started.
    """

    id: TableMaintenanceRunId
    table_uuid: TableId
    trigger: TriggerType
    operation: MaintenanceOperation
    created_at: datetime
    execution_ref: str
    priority: TablePriority = TablePriority.P3
    status: RunStatusField = PendingRunStatus()
    content: MaintenanceJobContent
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
    def _content_is_of_its_operation(self) -> TableMaintenanceRun:
        if msg := _misplaced_content(self.operation, self.content):
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _a_skip_reason_only_when_skipped(self) -> TableMaintenanceRun:
        if (self.skip_reason is not None) != (self.status.name is RunStatusName.SKIPPED):
            msg = f"a run has a skip reason exactly when it is skipped: run {self.id} is {self.status.name}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _a_finish_time_only_when_terminal(self) -> TableMaintenanceRun:
        if (self.finished_at is not None) != self.status.is_terminal:
            msg = (
                f"a run has a finish time exactly when it has ended (succeeded, failed, skipped or cancelled): "
                f"run {self.id} is {self.status.name}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _status_is_the_latest_attempts(self) -> TableMaintenanceRun:
        latest = self.attempts[-1] if self.attempts else None
        if self.status.name in _statuses_agreeing_with(latest):
            return self
        if latest is None:
            msg = f"run {self.id} has no attempt, so it is pending, skipped or cancelled, not {self.status.name}"
        else:
            msg = (
                f"a run reads its latest attempt's status: run {self.id} is {self.status.name}, "
                f"attempt {latest.attempt} is {latest.status} with next step {latest.next_step}"
            )
        raise ValueError(msg)

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
        content: MaintenanceJobContent,
        priority: TablePriority = TablePriority.P3,
    ) -> TableMaintenanceRun:
        """Create a pending run of one operation.

        ``execution_ref`` names the execution that runs it, so a result
        that only carries the run id can still be routed to that execution.
        ``priority`` is the priority the run was started with. ``content`` is what every attempt does,
        and must be the content of ``operation``.
        """
        if not execution_ref:
            msg = "a maintenance run needs the execution reference that runs it"
            raise ValueError(msg)
        if msg := _misplaced_content(operation, content):
            raise InvalidRunTransition(msg)
        return cls(
            id=id,
            table_uuid=table_uuid,
            trigger=trigger,
            operation=operation,
            created_at=now,
            execution_ref=execution_ref,
            priority=priority,
            content=content,
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

        The attempt stays queued until ``record_attempt_running`` says its coordinator runs. Starting the
        attempt that is already queued or running is a no-op, except that a given ``job_name`` is
        attached when none is recorded yet. A pending run starts its first attempt and a run waiting to
        retry its next one; no other run starts one. A new attempt clears the previous attempt's outcome
        from the run.
        """
        if attempt == self.current_attempt and self.status.is_in_flight:
            if job_name is not None:
                self.attach_job_name(attempt, job_name)
            return
        queued = self._next_status(self.status.start_attempt)
        if attempt != self.current_attempt + 1:
            msg = f"cannot start attempt {attempt} of run {self.id}: its next attempt is {self.current_attempt + 1}"
            raise InvalidRunTransition(msg)
        self._assign_together(
            status=queued,
            finished_at=None,
            error=None,
            metrics={},
            attempts=(
                *self.attempts,
                OperationAttempt(
                    attempt=attempt, size=size, status=AttemptStatus.QUEUED, started_at=now, job_name=job_name
                ),
            ),
        )

    def raise_priority(self, priority: TablePriority) -> bool:
        """Raise the run to ``priority`` and tell whether it was raised.

        Only a priority that outranks the run's raises it, and only while the run has not ended; an equal
        or lower one, or an ended run, changes nothing. A run ends when it succeeded, failed, was cancelled
        or was skipped; a run waiting to retry still takes a raise, so the retry submits at the new priority.
        """
        if self.status.is_terminal or not priority.outranks(self.priority):
            return False
        self.priority = priority
        return True

    def attempt_record(self, attempt: int) -> OperationAttempt | None:
        """Return one attempt of the run, or None when it has none by that number."""
        return next((a for a in self.attempts if a.attempt == attempt), None)

    def record_attempt_running(self, attempt: int, started_running_at: datetime, now: datetime) -> None:
        """Record that the coordinator of an attempt started running at ``started_running_at``.

        The time is clamped into the attempt's submit time and ``now``. A queued attempt becomes
        running; a running one is left alone; a finished attempt that has no running time only gets
        it, within its own span, and keeps its status. A report for an earlier attempt is ignored.
        """
        record = self._current_record(attempt)
        if record is None or record.status is AttemptStatus.RUNNING:
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
            status=self._next_status(self.status.mark_running),
            attempts=self._with_attempt(
                attempt,
                status=AttemptStatus.RUNNING,
                started_running_at=self._clamp(started_running_at, record.started_at, now),
            ),
        )

    def attach_job_name(self, attempt: int, job_name: str) -> None:
        """Record the job of the queued or running attempt; repeating the same name is a no-op."""
        if attempt != self.current_attempt or not self.status.is_in_flight:
            msg = (
                f"cannot attach a job to attempt {attempt} of run {self.id} "
                f"(status {self.status.name}, attempts {self.current_attempt})"
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

        Recording the success again, or a result of an earlier attempt, is a no-op. ``started_running_at``
        fills the attempt's running time when it has none.
        """
        record = self._current_record(attempt)
        if record is None or record.status is AttemptStatus.SUCCEEDED:
            return
        self._end_attempt(
            record,
            self._next_status(self.status.succeed),
            AttemptStatus.SUCCEEDED,
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

        A retry to follow leaves the run waiting to retry, with no finish time, until ``start_attempt``
        queues the next attempt; with none the run fails and finishes. Recording a failure of an attempt
        already failed, or a result of an earlier attempt, is a no-op. ``started_running_at`` fills the
        attempt's running time when it has none.
        """
        record = self._current_record(attempt)
        if record is None or record.status is AttemptStatus.FAILED:
            return
        retries = next_attempt is not None and next_attempt.step.retries
        self._end_attempt(
            record,
            self._next_status(lambda: self.status.fail(retries=retries)),
            AttemptStatus.FAILED,
            now,
            started_running_at=started_running_at,
            metrics={},
            error=error,
            failure_class=failure_class,
            event_log_finished=event_log_finished,
            next_step=next_attempt.step if next_attempt else None,
            next_size=next_attempt.size if next_attempt else None,
        )

    def cancel_attempt(
        self,
        attempt: int,
        error: str,
        now: datetime,
        *,
        started_running_at: datetime | None = None,
        event_log_finished: bool | None = None,
    ) -> None:
        """Record that the attempt in flight was cancelled: it failed as cancelled, and the run is cancelled.

        Cancelling an attempt already failed, or an earlier attempt, is a no-op. ``started_running_at``
        fills the attempt's running time when it has none.
        """
        record = self._current_record(attempt)
        if record is None or record.status is AttemptStatus.FAILED:
            return
        self._end_attempt(
            record,
            self._next_status(self.status.cancel),
            AttemptStatus.FAILED,
            now,
            started_running_at=started_running_at,
            metrics={},
            error=error,
            failure_class=FailureClass.CANCELLED,
            event_log_finished=event_log_finished,
            next_step=NextStep.CANCELLED,
            next_size=None,
        )

    def cancel(self, now: datetime) -> None:
        """Cancel a run with no attempt in flight: one still pending or waiting to retry.

        A run whose attempt is queued or running is cancelled through that attempt, with
        ``cancel_attempt``; a run that has ended cannot be cancelled.
        """
        if self.status.is_in_flight:
            msg = (
                f"run {self.id} has attempt {self.current_attempt} in flight ({self.status.name}): "
                f"cancel it with cancel_attempt"
            )
            raise InvalidRunTransition(msg)
        self._assign_together(status=self._next_status(self.status.cancel), finished_at=now)

    def skip(self, reason: str, now: datetime) -> None:
        """Skip a run that never started, saying why."""
        self._assign_together(status=self._next_status(self.status.skip), skip_reason=reason, finished_at=now)

    def _next_status(self, move: Callable[[], RunStatus]) -> RunStatus:
        """Return the status ``move`` leads to, naming this run when the current status refuses it."""
        try:
            return move()
        except InvalidRunTransition as refusal:
            msg = f"run {self.id}: {refusal}"
            raise InvalidRunTransition(msg) from refusal

    def _current_record(self, attempt: int) -> OperationAttempt | None:
        """Return the current attempt when ``attempt`` is it, None for an earlier one; refuse a later one."""
        if attempt < self.current_attempt:
            return None
        if attempt > self.current_attempt or not self.attempts:
            msg = f"attempt {attempt} of run {self.id} was never started"
            raise InvalidRunTransition(msg)
        return self.attempts[-1]

    def _end_attempt(
        self,
        record: OperationAttempt,
        status: RunStatus,
        attempt_status: AttemptStatus,
        now: datetime,
        *,
        started_running_at: datetime | None,
        metrics: dict[str, Any],
        error: str | None,
        **outcome: object,
    ) -> None:
        """End the attempt ``record`` as ``attempt_status`` and move the run to ``status``.

        The run gets a finish time only when ``status`` ends it, and loses the one it had otherwise.
        """
        self._assign_together(
            status=status,
            finished_at=now if status.is_terminal else None,
            metrics=metrics,
            error=error,
            attempts=self._with_attempt(
                record.attempt,
                status=attempt_status,
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
