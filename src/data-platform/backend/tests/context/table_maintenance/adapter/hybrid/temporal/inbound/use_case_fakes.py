"""Recording fakes of the inbound use cases wrapped by the Temporal activities."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ReleaseCompactionCandidatesUseCase,
    ReleaseCompactionCandidatesUseCaseInput,
    ReleaseCompactionCandidatesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    SyncDiscoveredTablesUseCase,
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunUseCase,
    CreateTableMaintenanceRunUseCaseInput,
    CreateTableMaintenanceRunUseCaseOutput,
    DeleteMaintenanceJobUseCase,
    DeleteMaintenanceJobUseCaseInput,
    DeleteMaintenanceJobUseCaseOutput,
    GetMaintenanceJobStatusUseCase,
    GetMaintenanceJobStatusUseCaseInput,
    GetMaintenanceJobStatusUseCaseOutput,
    RecordTableMaintenanceOperationResultUseCase,
    RecordTableMaintenanceOperationResultUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseOutput,
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
            reconcile_interval_seconds=3600,
            table_name="iceberg.sales.orders",
            operations=(
                PlanTableMaintenanceUseCaseOutput.Operation(
                    operation="rewrite_data_files",
                    filters=(PlanTableMaintenanceUseCaseOutput.Filter(spec_id=0, where="x = 1"),),
                    procedure_args={"strategy": "binpack"},
                ),
            ),
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


class FakeCreateRun(CreateTableMaintenanceRunUseCase):
    """Create run use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[CreateTableMaintenanceRunUseCaseInput] = []

    def execute(self, request: CreateTableMaintenanceRunUseCaseInput) -> CreateTableMaintenanceRunUseCaseOutput:
        """Record the request and return a running run."""
        self.requests.append(request)
        return CreateTableMaintenanceRunUseCaseOutput(
            run_id=request.run_id,
            table_uuid=request.table_uuid,
            execution_ref=request.execution_ref,
            trigger=request.trigger,
            status="running",
            operations=[{"operation": op} for op in request.operations],
            created_at=CREATED_AT,
            finished_at=None,
        )


class FakeRecordResult(RecordTableMaintenanceOperationResultUseCase):
    """Record result use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[RecordTableMaintenanceOperationResultUseCaseInput] = []

    def execute(
        self, request: RecordTableMaintenanceOperationResultUseCaseInput
    ) -> RecordTableMaintenanceOperationResultUseCaseOutput:
        """Record the request and return its run as running."""
        self.requests.append(request)
        return RecordTableMaintenanceOperationResultUseCaseOutput(run_id=request.run_id, status="running")


class FakeReleaseCandidates(ReleaseCompactionCandidatesUseCase):
    """Release compaction candidates use case fake that records its requests."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[ReleaseCompactionCandidatesUseCaseInput] = []

    def execute(self, request: ReleaseCompactionCandidatesUseCaseInput) -> ReleaseCompactionCandidatesUseCaseOutput:
        """Record the request and report two candidates released."""
        self.requests.append(request)
        return ReleaseCompactionCandidatesUseCaseOutput(released=2)


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
