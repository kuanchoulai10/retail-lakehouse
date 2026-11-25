"""Recording fakes of the inbound use cases wrapped by the Temporal activities."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    SyncDiscoveredTablesUseCase,
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CancelTableMaintenanceRunUseCase,
    CancelTableMaintenanceRunUseCaseInput,
    CancelTableMaintenanceRunUseCaseOutput,
    CreateTableMaintenanceRunsUseCase,
    CreateTableMaintenanceRunsUseCaseInput,
    CreateTableMaintenanceRunsUseCaseOutput,
    DeleteMaintenanceJobUseCase,
    DeleteMaintenanceJobUseCaseInput,
    DeleteMaintenanceJobUseCaseOutput,
    GetMaintenanceJobStatusUseCase,
    GetMaintenanceJobStatusUseCaseInput,
    GetMaintenanceJobStatusUseCaseOutput,
    RaiseTableMaintenanceRunPriorityUseCase,
    RaiseTableMaintenanceRunPriorityUseCaseInput,
    RaiseTableMaintenanceRunPriorityUseCaseOutput,
    RecordMaintenanceAttemptRunningUseCase,
    RecordMaintenanceAttemptRunningUseCaseInput,
    RecordMaintenanceAttemptRunningUseCaseOutput,
    RecordTableMaintenanceOperationResultUseCase,
    RecordTableMaintenanceOperationResultUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseOutput,
    SkipTableMaintenanceRunUseCase,
    SkipTableMaintenanceRunUseCaseInput,
    SkipTableMaintenanceRunUseCaseOutput,
    SubmitMaintenanceOperationUseCase,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCase,
    RecordTableReconciliationUseCaseInput,
    RecordTableReconciliationUseCaseOutput,
)

CREATED_AT = datetime(2026, 10, 24, tzinfo=UTC)
GOLD_POLICY_ID = "mp-00000000000000000000000003"


class FakePlan(PlanTableMaintenanceUseCase):
    """Plan use case fake that records its requests."""

    def __init__(self, output: PlanTableMaintenanceUseCaseOutput | None = None) -> None:
        """Hold the plan to return, a fixed one by default, and start with no recorded requests."""
        self.requests: list[PlanTableMaintenanceUseCaseInput] = []
        self._output = output

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Record the request and return the plan it holds."""
        self.requests.append(request)
        if self._output is not None:
            return self._output
        return PlanTableMaintenanceUseCaseOutput(
            status="planned",
            reason=None,
            schedule_interval_seconds=3600,
            catalog_commit_debounce_seconds=300,
            table_name="iceberg.sales.orders",
            operations=(
                PlanTableMaintenanceUseCaseOutput.Operation(
                    operation="rewrite_data_files",
                    content={
                        "operation": "rewrite_data_files",
                        "target_file_size_bytes": 536870912,
                        "options": {"strategy": "binpack"},
                        "partitions": [],
                    },
                ),
            ),
            policy_id=GOLD_POLICY_ID,
            policy_name="gold",
            policy_version=3,
            policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
        )


class FakeSubmit(SubmitMaintenanceOperationUseCase):
    """Submit use case fake that records its requests and can fail."""

    def __init__(self, error: Exception | None = None) -> None:
        """Hold the error to raise and start with no recorded requests."""
        self.requests: list[SubmitMaintenanceOperationUseCaseInput] = []
        self._error = error

    def execute(self, request: SubmitMaintenanceOperationUseCaseInput) -> SubmitMaintenanceOperationUseCaseOutput:
        """Record the request and raise the configured error, or return a fixed job name."""
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return SubmitMaintenanceOperationUseCaseOutput(job_name="app-1")


class FakeStatus(GetMaintenanceJobStatusUseCase):
    """Status use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[GetMaintenanceJobStatusUseCaseInput] = []

    def execute(self, request: GetMaintenanceJobStatusUseCaseInput) -> GetMaintenanceJobStatusUseCaseOutput:
        """Record the request and return a failed state with an out of memory error."""
        self.requests.append(request)
        return GetMaintenanceJobStatusUseCaseOutput(state="FAILED", error="oom")


class FakeDelete(DeleteMaintenanceJobUseCase):
    """Delete use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[DeleteMaintenanceJobUseCaseInput] = []

    def execute(self, request: DeleteMaintenanceJobUseCaseInput) -> DeleteMaintenanceJobUseCaseOutput:
        """Record the request and return the attempt it deleted."""
        self.requests.append(request)
        return DeleteMaintenanceJobUseCaseOutput(
            run_id=request.run_id,
            operation=request.operation,
            attempt=request.attempt,
        )


class FakeCreateRuns(CreateTableMaintenanceRunsUseCase):
    """Create runs use case fake that records its requests and reports every run created."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[CreateTableMaintenanceRunsUseCaseInput] = []

    def execute(self, request: CreateTableMaintenanceRunsUseCaseInput) -> CreateTableMaintenanceRunsUseCaseOutput:
        """Record the request and report the ids of its runs."""
        self.requests.append(request)
        return CreateTableMaintenanceRunsUseCaseOutput(run_ids=tuple(run.run_id for run in request.runs))


class FakeRecordResult(RecordTableMaintenanceOperationResultUseCase):
    """Record result use case fake that records its requests."""

    def __init__(self, output: RecordTableMaintenanceOperationResultUseCaseOutput | None = None) -> None:
        """Hold the reply to return, its run as running by default, and start with no recorded requests."""
        self.requests: list[RecordTableMaintenanceOperationResultUseCaseInput] = []
        self._output = output

    def execute(
        self, request: RecordTableMaintenanceOperationResultUseCaseInput
    ) -> RecordTableMaintenanceOperationResultUseCaseOutput:
        """Record the request and return the reply it holds, or its run as running."""
        self.requests.append(request)
        if self._output is not None:
            return self._output
        return RecordTableMaintenanceOperationResultUseCaseOutput(run_id=request.run_id, status="running")


class FakeRecordReconciliation(RecordTableReconciliationUseCase):
    """Record reconciliation use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[RecordTableReconciliationUseCaseInput] = []

    def execute(self, request: RecordTableReconciliationUseCaseInput) -> RecordTableReconciliationUseCaseOutput:
        """Record the request and report it recorded."""
        self.requests.append(request)
        return RecordTableReconciliationUseCaseOutput(recorded=True)


class FakeSync(SyncDiscoveredTablesUseCase):
    """Sync use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[SyncDiscoveredTablesUseCaseInput] = []

    def execute(self, request: SyncDiscoveredTablesUseCaseInput) -> SyncDiscoveredTablesUseCaseOutput:
        """Record the request and return fixed registered, renamed, dropped and skipped counts."""
        self.requests.append(request)
        return SyncDiscoveredTablesUseCaseOutput(registered=1, renamed=2, dropped=3, skipped=4)


class FakeRecordRunning(RecordMaintenanceAttemptRunningUseCase):
    """Record running use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[RecordMaintenanceAttemptRunningUseCaseInput] = []

    def execute(
        self, request: RecordMaintenanceAttemptRunningUseCaseInput
    ) -> RecordMaintenanceAttemptRunningUseCaseOutput:
        """Record the request and return the attempt as running since the time it was given."""
        self.requests.append(request)
        return RecordMaintenanceAttemptRunningUseCaseOutput(
            status="running", started_running_at=request.started_running_at
        )


class FakeRaisePriority(RaiseTableMaintenanceRunPriorityUseCase):
    """Raise priority use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[RaiseTableMaintenanceRunPriorityUseCaseInput] = []

    def execute(
        self, request: RaiseTableMaintenanceRunPriorityUseCaseInput
    ) -> RaiseTableMaintenanceRunPriorityUseCaseOutput:
        """Record the request and return the run as raised to the priority it was given, P0 when none."""
        self.requests.append(request)
        return RaiseTableMaintenanceRunPriorityUseCaseOutput(priority=request.priority or "P0", raised=True)


class FakeSkip(SkipTableMaintenanceRunUseCase):
    """Skip run use case fake that records its requests."""

    def __init__(
        self, output: SkipTableMaintenanceRunUseCaseOutput | None = None, *, error: Exception | None = None
    ) -> None:
        """Hold the reply to return (the run skipped by default) or the error to raise, with no recorded requests."""
        self.requests: list[SkipTableMaintenanceRunUseCaseInput] = []
        self._output = output
        self._error = error

    def execute(self, request: SkipTableMaintenanceRunUseCaseInput) -> SkipTableMaintenanceRunUseCaseOutput:
        """Record the request and raise the error it holds, or return its reply, or the run as skipped."""
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        if self._output is not None:
            return self._output
        return SkipTableMaintenanceRunUseCaseOutput(run_id=request.run_id, status="skipped", skipped=True)


class FakeCancel(CancelTableMaintenanceRunUseCase):
    """Cancel run use case fake that records its requests."""

    def __init__(
        self, output: CancelTableMaintenanceRunUseCaseOutput | None = None, *, error: Exception | None = None
    ) -> None:
        """Hold the reply to return (the run cancelled by default) or the error to raise, with no recorded requests."""
        self.requests: list[CancelTableMaintenanceRunUseCaseInput] = []
        self._output = output
        self._error = error

    def execute(self, request: CancelTableMaintenanceRunUseCaseInput) -> CancelTableMaintenanceRunUseCaseOutput:
        """Record the request and raise the error it holds, or return its reply, or the run as cancelled."""
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        if self._output is not None:
            return self._output
        return CancelTableMaintenanceRunUseCaseOutput(run_id=request.run_id, status="cancelled", cancelled=True)
