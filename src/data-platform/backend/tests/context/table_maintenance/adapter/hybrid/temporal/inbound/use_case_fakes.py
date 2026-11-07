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

CREATED_AT = datetime(2026, 10, 24, tzinfo=UTC)


class FakePlan(PlanTableMaintenanceUseCase):
    def __init__(self) -> None:
        self.requests: list[PlanTableMaintenanceUseCaseInput] = []

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
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
    def __init__(self, error: Exception | None = None) -> None:
        self.requests: list[SubmitMaintenanceOperationUseCaseInput] = []
        self._error = error

    def execute(self, request: SubmitMaintenanceOperationUseCaseInput) -> SubmitMaintenanceOperationUseCaseOutput:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return SubmitMaintenanceOperationUseCaseOutput(job_name="app-1")


class FakeStatus(GetMaintenanceJobStatusUseCase):
    def __init__(self) -> None:
        self.requests: list[GetMaintenanceJobStatusUseCaseInput] = []

    def execute(self, request: GetMaintenanceJobStatusUseCaseInput) -> GetMaintenanceJobStatusUseCaseOutput:
        self.requests.append(request)
        return GetMaintenanceJobStatusUseCaseOutput(state="FAILED", error="oom")


class FakeDelete(DeleteMaintenanceJobUseCase):
    def __init__(self) -> None:
        self.requests: list[DeleteMaintenanceJobUseCaseInput] = []

    def execute(self, request: DeleteMaintenanceJobUseCaseInput) -> DeleteMaintenanceJobUseCaseOutput:
        self.requests.append(request)
        return DeleteMaintenanceJobUseCaseOutput(
            run_id=request.run_id,
            operation=request.operation,
            attempt=request.attempt,
        )


class FakeCreateRun(CreateTableMaintenanceRunUseCase):
    def __init__(self) -> None:
        self.requests: list[CreateTableMaintenanceRunUseCaseInput] = []

    def execute(self, request: CreateTableMaintenanceRunUseCaseInput) -> CreateTableMaintenanceRunUseCaseOutput:
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
    def __init__(self) -> None:
        self.requests: list[RecordTableMaintenanceOperationResultUseCaseInput] = []

    def execute(
        self, request: RecordTableMaintenanceOperationResultUseCaseInput
    ) -> RecordTableMaintenanceOperationResultUseCaseOutput:
        self.requests.append(request)
        return RecordTableMaintenanceOperationResultUseCaseOutput(run_id=request.run_id, status="running")


class FakeSync(SyncDiscoveredTablesUseCase):
    def __init__(self) -> None:
        self.requests: list[SyncDiscoveredTablesUseCaseInput] = []

    def execute(self, request: SyncDiscoveredTablesUseCaseInput) -> SyncDiscoveredTablesUseCaseOutput:
        self.requests.append(request)
        return SyncDiscoveredTablesUseCaseOutput(registered=1, renamed=2, dropped=3, skipped=4)
