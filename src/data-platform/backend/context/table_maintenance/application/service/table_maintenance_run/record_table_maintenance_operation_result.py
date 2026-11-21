"""Define the RecordTableMaintenanceOperationResultService."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    PeakHeapUse,
    RecordedAttempt,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptEnding,
    ContainerExit,
    FailureEvidence,
    NextStep,
    TableMaintenanceRunId,
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
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
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
from context.table_maintenance.application.service.shared import applied_policy_ref_of, translate_domain_errors
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
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCase,
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
_PEAK_DRIVER_HEAP_BYTES = "peak_driver_heap_bytes"
_PEAK_EXECUTOR_HEAP_BYTES = "peak_executor_heap_bytes"
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
        resolve_applicable_policy: ResolveApplicableTableMaintenancePolicyUseCase,
        *,
        size_memory: Mapping[ComputeSize, SizeMemory],
    ) -> None:
        """Bind the repos, the evidence readers, the applicable policy resolution and each size's memory.

        A size missing from ``size_memory`` is never stepped down to.
        """
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo
        self._evidence_gateway = evidence_gateway
        self._event_log_gateway = event_log_gateway
        self._resolve_applicable_policy = resolve_applicable_policy
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
        the run's is a conflict and changes nothing.
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
        with translate_domain_errors():
            if request.attempt < run.current_attempt:
                return _output(run, run.attempt_record(request.attempt))
            if _already_recorded(run, request):
                self._record_on_table(run, operation, run.attempt_record(request.attempt), request)
                return _output(run, run.attempt_record(request.attempt))
            record = run.attempt_record(request.attempt)
            size = record.size if record else None
            evidence = self._read_evidence(request, ending)
            event_log_finished = self._read_event_log(evidence)
            if request.succeeded:
                run.succeed(
                    request.attempt,
                    request.metrics,
                    request.now,
                    started_running_at=_driver_started_at(evidence),
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
        size: ComputeSize | None,
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
            started_running_at=_driver_started_at(evidence),
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
        attempt = RecordedAttempt(run_id=request.run_id, attempt=request.attempt)
        if table.has_recorded(operation, attempt):
            return
        size = record.size if record else None
        if request.succeeded:
            ran_at = size or ComputeSize.S
            peak = PeakHeapUse(
                driver_bytes=_measured(request.metrics.get(_PEAK_DRIVER_HEAP_BYTES)),
                executor_bytes=_measured(request.metrics.get(_PEAK_EXECUTOR_HEAP_BYTES)),
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
        policy, name = self._planned_policy(table, request)
        mark = AttentionMark(
            since=request.now,
            reason=_NEEDS_ATTENTION_REASON,
            policy=policy,
            policy_name=TableMaintenancePolicyName(value=name),
        )
        table.mark_needs_attention(operation, mark, request.now)

    def _planned_policy(
        self, table: Table, request: RecordTableMaintenanceOperationResultUseCaseInput
    ) -> tuple[AppliedPolicyRef, str]:
        """Return the policy the run was planned under and its name then.

        When the request does not say, the policy applying now and its current name.
        """
        if request.policy_id is not None and request.policy_version is not None and request.policy_name is not None:
            ref = AppliedPolicyRef(
                policy_id=TableMaintenancePolicyId(request.policy_id),
                version=request.policy_version,
                target=request.policy_target,
            )
            return ref, request.policy_name
        applied = self._resolve_applicable_policy.execute(
            ResolveApplicableTableMaintenancePolicyUseCaseInput(
                catalog=table.name.catalog,
                table_uuid=table.id.value,
                namespace=table.name.namespace,
                table=table.name.table,
            )
        )
        return applied_policy_ref_of(applied), applied.policy_name


def _driver_started_at(evidence: ReadMaintenanceJobEvidenceGatewayOutput | None) -> datetime | None:
    """Return when the attempt's driver started as the evidence reports it, or None when it does not."""
    if evidence is None or evidence.driver_started_at is None:
        return None
    return datetime.fromisoformat(evidence.driver_started_at)


def _measured(value: int | None) -> int | None:
    """Return a measured byte count, or None when the job did not measure it or reported nonsense."""
    return value if value is not None and value >= 0 else None


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
