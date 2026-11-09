"""Recording fakes of the inbound use cases wrapped by the Temporal activities."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    PlanTableMaintenanceUseCaseOutputFilterItem,
    PlanTableMaintenanceUseCaseOutputItem,
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

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: list[PlanTableMaintenanceUseCaseInput] = []

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Record the request and return a fixed plan."""
        self.requests.append(request)
        return PlanTableMaintenanceUseCaseOutput(
            status="planned",
            reason=None,
            reconcile_interval_seconds=3600,
            table_name="iceberg.sales.orders",
            operations=[
                PlanTableMaintenanceUseCaseOutputItem(
                    operation="rewrite_data_files",
                    filters=[PlanTableMaintenanceUseCaseOutputFilterItem(0, "x = 1")],
                    procedure_args={"strategy": "binpack"},
                )
            ],
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
