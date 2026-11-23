"""Define the RecordTableMaintenanceOperationResultService."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TableMaintenancePolicyId,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    PeakMemoryUse,
    RecordedAttempt,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import TableMaintenancePolicyName
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptEnding,
    ContainerExit,
    FailureEvidence,
    InvalidRunTransition,
    NextStep,
    RunStatus,
)
from context.table_maintenance.application.domain.service.table import fits_smaller_size
from context.table_maintenance.application.domain.service.table_maintenance_run import (
    classify_attempt_failure,
    decide_next_attempt,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RecordTableMaintenanceOperationResultUseCase,
    RecordTableMaintenanceOperationResultUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceEventLogGatewayInput,
    ReadMaintenanceJobEvidenceGatewayInput,
)
from context.table_maintenance.application.service.shared import policy_target_of, translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_run.require_run_operation import (
    require_run_operation,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from enum import StrEnum

    from context.table_maintenance.application.domain.model.shared import SizeMemory
    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        OperationAttempt,
        TableMaintenanceRun,
    )
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceEventLogGateway,
        ReadMaintenanceJobEvidenceGateway,
        ReadMaintenanceJobEvidenceGatewayOutput,
        TableMaintenanceRunsRepo,
    )

logger = logging.getLogger(__name__)

_UNKNOWN_ERROR = "unknown error"
_PEAK_COORDINATOR_MEMORY_BYTES = "peak_coordinator_memory_bytes"
_PEAK_WORKER_MEMORY_BYTES = "peak_worker_memory_bytes"
_ENDINGS_WITH_EVIDENCE = frozenset({AttemptEnding.RESULT, AttemptEnding.JOB_FAILED})
_NEEDS_ATTENTION_REASON = "out of memory at size L"


class RecordTableMaintenanceOperationResultService(RecordTableMaintenanceOperationResultUseCase):
    """Record the outcome of a run's attempt, why it failed and what follows it, on the run and the table."""

    def __init__(
        self,
        runs_repo: TableMaintenanceRunsRepo,
        tables_repo: TablesRepo,
        evidence_gateway: ReadMaintenanceJobEvidenceGateway,
        event_log_gateway: ReadMaintenanceEventLogGateway,
        *,
        size_memory: Mapping[ComputeSize, SizeMemory],
    ) -> None:
        """Bind the repos, the evidence readers and each size's memory.

        A size missing from ``size_memory`` is never stepped down to.
        """
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo
        self._evidence_gateway = evidence_gateway
        self._event_log_gateway = event_log_gateway
        self._size_memory = dict(size_memory)

    def execute(
        self, request: RecordTableMaintenanceOperationResultUseCaseInput
    ) -> RecordTableMaintenanceOperationResultUseCaseOutput:
        """Classify and decide the attempt, update the run, then the table.

        Two aggregates are updated in sequence, not atomically: the run is saved
        first, then the table. A replay of an outcome the run already holds reads
        nothing and returns what the run holds for that attempt, but still brings
        the table up to date, so a retry after a crash between the two saves
        loses no table update; the table takes each attempt in once. A stale
        lower attempt changes nothing. A result naming an operation other than
        the run's is a conflict and changes nothing. A run still pending (its first
        submit never saved the attempt: a cancel or a refused submit stopped it
        first) has nothing to record: the reply says ``pending`` and nothing is
        saved, so the caller can tell the attempt never started.
        """
        try:
            operation = MaintenanceOperation(request.operation)
            ending = AttemptEnding(request.ended_by)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        require_run_operation(run, operation)
        if run.status is RunStatus.PENDING:
            return _output(run, None)
        with translate_domain_errors():
            if request.attempt < run.current_attempt:
                return _output(run, run.attempt_record(request.attempt))
            if _already_recorded(run, request):
                self._record_on_table(run, operation, run.attempt_record(request.attempt), request)
                return _output(run, run.attempt_record(request.attempt))
            size = _started_attempt(run, request.attempt).size
            evidence = self._read_evidence(request, ending)
            event_log_finished = self._read_event_log(evidence)
            if request.succeeded:
                run.succeed(
                    request.attempt,
                    request.metrics,
                    request.now,
                    started_running_at=_started_running_at(evidence),
                    event_log_finished=event_log_finished,
                )
            else:
                self._fail(run, ending, size, request, evidence, event_log_finished)
            self._runs_repo.update(run)
            self._record_on_table(run, operation, run.attempt_record(request.attempt), request)
        return _output(run, run.attempt_record(request.attempt))

    def _fail(
        self,
        run: TableMaintenanceRun,
        ending: AttemptEnding,
        size: ComputeSize,
        request: RecordTableMaintenanceOperationResultUseCaseInput,
        evidence: ReadMaintenanceJobEvidenceGatewayOutput | None,
        event_log_finished: bool | None,
    ) -> None:
        error = request.error or _UNKNOWN_ERROR
        texts = tuple(t for t in (error, evidence.error if evidence else None) if t)
        containers = tuple(
            ContainerExit(role=c.role, reason=c.reason, exit_code=c.exit_code, message=c.message)
            for c in (evidence.containers if evidence else ())
        )
        failure_class = classify_attempt_failure(FailureEvidence(ended_by=ending, texts=texts, containers=containers))
        next_attempt = decide_next_attempt(
            failure_class, size, request.attempt, request.max_attempts, still_running=request.still_running
        )
        run.fail(
            request.attempt,
            error,
            request.now,
            failure_class=failure_class,
            started_running_at=_started_running_at(evidence),
            event_log_finished=event_log_finished,
            next_attempt=next_attempt,
        )

    def _read_evidence(
        self, request: RecordTableMaintenanceOperationResultUseCaseInput, ending: AttemptEnding
    ) -> ReadMaintenanceJobEvidenceGatewayOutput | None:
        """Return what the attempt's job left behind, or None when Spark did not end it or it cannot be read.

        The platform's own endings (a timeout, a cancel, a vanished job, or a failed submit)
        leave nothing of Spark's worth reading.
        """
        if ending not in _ENDINGS_WITH_EVIDENCE:
            return None
        try:
            return self._evidence_gateway.read(
                ReadMaintenanceJobEvidenceGatewayInput(
                    run_id=request.run_id, operation=request.operation, attempt=request.attempt
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "cannot read the job evidence of attempt %s of %s in run %s: %s",
                request.attempt,
                request.operation,
                request.run_id,
                exc,
            )
            return None

    def _read_event_log(self, evidence: ReadMaintenanceJobEvidenceGatewayOutput | None) -> bool | None:
        """Return whether the attempt's event log finished, or None when that is unknown."""
        if evidence is None or evidence.execution_id is None:
            return None
        try:
            return self._event_log_gateway.read(
                ReadMaintenanceEventLogGatewayInput(execution_id=evidence.execution_id)
            ).finished
        except Exception as exc:  # noqa: BLE001
            logger.warning("cannot read the event log of %s: %s", evidence.execution_id, exc)
            return None

    def _record_on_table(
        self,
        run: TableMaintenanceRun,
        operation: MaintenanceOperation,
        record: OperationAttempt | None,
        request: RecordTableMaintenanceOperationResultUseCaseInput,
    ) -> None:
        """Take the attempt's outcome, as the run recorded it, into the table, once per attempt."""
        table = self._tables_repo.get(run.table_uuid)
        if table is None or table.status == TableStatus.DROPPED:
            return
        attempt = RecordedAttempt(run_id=TableMaintenanceRunId(request.run_id), attempt=request.attempt)
        if table.has_recorded(operation, attempt):
            return
        if request.succeeded:
            ran_at = _started_attempt(run, request.attempt).size
            peak = PeakMemoryUse(
                coordinator_bytes=_measured(request.metrics.get(_PEAK_COORDINATOR_MEMORY_BYTES)),
                worker_bytes=_measured(request.metrics.get(_PEAK_WORKER_MEMORY_BYTES)),
            )
            table.record_operation_result(
                operation,
                True,
                request.now,
                size=ran_at,
                fits_smaller=fits_smaller_size(ran_at, peak, self._size_memory),
                attempt=attempt,
            )
        else:
            table.record_operation_result(operation, False, request.now, attempt=attempt)
            if record is not None and record.next_step is NextStep.NEEDS_ATTENTION:
                self._mark_needs_attention(table, operation, request)
        self._tables_repo.update(table)

    def _mark_needs_attention(
        self,
        table: Table,
        operation: MaintenanceOperation,
        request: RecordTableMaintenanceOperationResultUseCaseInput,
    ) -> None:
        mark = AttentionMark(
            since=request.now,
            reason=_NEEDS_ATTENTION_REASON,
            policy=_planned_policy(request),
            policy_name=TableMaintenancePolicyName(value=request.policy_name),
        )
        table.mark_needs_attention(operation, mark, request.now)


def _planned_policy(request: RecordTableMaintenanceOperationResultUseCaseInput) -> AppliedPolicyRef:
    """Return the policy the run was planned under, as the request names it."""
    return AppliedPolicyRef(
        policy_id=TableMaintenancePolicyId(request.policy_id),
        version=request.policy_version,
        target=policy_target_of(request.policy_target),
    )


def _started_running_at(evidence: ReadMaintenanceJobEvidenceGatewayOutput | None) -> datetime | None:
    """Return when the attempt's coordinator started as the evidence reports it, or None when it does not."""
    if evidence is None or evidence.started_running_at is None:
        return None
    return datetime.fromisoformat(evidence.started_running_at)


def _measured(value: int | None) -> int | None:
    """Return a measured byte count, or None when the job did not measure it or reported nonsense."""
    return value if value is not None and value >= 0 else None


def _started_attempt(run: TableMaintenanceRun, attempt: int) -> OperationAttempt:
    """Return the run's attempt by number, refusing one the run never started."""
    record = run.attempt_record(attempt)
    if record is None:
        msg = f"attempt {attempt} of run {run.id} was never started"
        raise InvalidRunTransition(msg)
    return record


def _already_recorded(run: TableMaintenanceRun, request: RecordTableMaintenanceOperationResultUseCaseInput) -> bool:
    outcome = "succeeded" if request.succeeded else "failed"
    return run.current_attempt == request.attempt and run.status.value == outcome


def _output(
    run: TableMaintenanceRun, record: OperationAttempt | None
) -> RecordTableMaintenanceOperationResultUseCaseOutput:
    return RecordTableMaintenanceOperationResultUseCaseOutput(
        run_id=run.id.value,
        status=run.status.value,
        failure_class=_value(record.failure_class) if record else None,
        next_step=_value(record.next_step) if record else None,
        next_size=_value(record.next_size) if record else None,
    )


def _value(member: StrEnum | None) -> str | None:
    return None if member is None else member.value
