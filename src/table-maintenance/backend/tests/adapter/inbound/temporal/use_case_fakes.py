"""Recording fakes of the inbound use cases wrapped by the Temporal activities."""

from __future__ import annotations

from datetime import UTC, datetime

from application.port.inbound.table.sync_discovered_tables import (
    SyncDiscoveredTablesUseCase,
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from application.port.inbound.maintenance_run.create_maintenance_run import (
    CreateMaintenanceRunUseCase,
    CreateMaintenanceRunUseCaseInput,
    CreateMaintenanceRunUseCaseOutput,
)
from application.port.inbound.maintenance_run.record_maintenance_operation_result import (
    RecordMaintenanceOperationResultUseCase,
    RecordMaintenanceOperationResultUseCaseInput,
    RecordMaintenanceOperationResultUseCaseOutput,
)
from application.port.inbound.reconcile.delete_maintenance_job import (
    DeleteMaintenanceJobUseCase,
    DeleteMaintenanceJobUseCaseInput,
    DeleteMaintenanceJobUseCaseOutput,
)
from application.port.inbound.reconcile.get_maintenance_job_status import (
    GetMaintenanceJobStatusUseCase,
    GetMaintenanceJobStatusUseCaseInput,
    GetMaintenanceJobStatusUseCaseOutput,
)
from application.port.inbound.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceUseCase,
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    PlanTableMaintenanceUseCaseOutputFilterItem,
    PlanTableMaintenanceUseCaseOutputItem,
)
from application.port.inbound.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationUseCase,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseOutput,
)

CREATED_AT = datetime(2026, 10, 24, tzinfo=UTC)


class FakePlan(PlanTableMaintenanceUseCase):
    def __init__(self) -> None:
        self.requests: list[PlanTableMaintenanceUseCaseInput] = []

    def execute(
        self, request: PlanTableMaintenanceUseCaseInput
    ) -> PlanTableMaintenanceUseCaseOutput:
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

    def execute(
        self, request: SubmitMaintenanceOperationUseCaseInput
    ) -> SubmitMaintenanceOperationUseCaseOutput:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return SubmitMaintenanceOperationUseCaseOutput(app_name="app-1")


class FakeStatus(GetMaintenanceJobStatusUseCase):
    def __init__(self) -> None:
        self.requests: list[GetMaintenanceJobStatusUseCaseInput] = []

    def execute(
        self, request: GetMaintenanceJobStatusUseCaseInput
    ) -> GetMaintenanceJobStatusUseCaseOutput:
        self.requests.append(request)
        return GetMaintenanceJobStatusUseCaseOutput(state="FAILED", error="oom")


class FakeDelete(DeleteMaintenanceJobUseCase):
    def __init__(self) -> None:
        self.requests: list[DeleteMaintenanceJobUseCaseInput] = []

    def execute(
        self, request: DeleteMaintenanceJobUseCaseInput
    ) -> DeleteMaintenanceJobUseCaseOutput:
        self.requests.append(request)
        return DeleteMaintenanceJobUseCaseOutput(
            app_name=f"{request.run_id}-{request.operation}-{request.attempt}"
        )


class FakeCreateRun(CreateMaintenanceRunUseCase):
    def __init__(self) -> None:
        self.requests: list[CreateMaintenanceRunUseCaseInput] = []

    def execute(
        self, request: CreateMaintenanceRunUseCaseInput
    ) -> CreateMaintenanceRunUseCaseOutput:
        self.requests.append(request)
        return CreateMaintenanceRunUseCaseOutput(
            run_id=request.run_id,
            table_uuid=request.table_uuid,
            workflow_id=request.workflow_id,
            trigger=request.trigger,
            status="running",
            operations=[{"operation": op} for op in request.operations],
            created_at=CREATED_AT,
            finished_at=None,
        )


class FakeRecordResult(RecordMaintenanceOperationResultUseCase):
    def __init__(self) -> None:
        self.requests: list[RecordMaintenanceOperationResultUseCaseInput] = []

    def execute(
        self, request: RecordMaintenanceOperationResultUseCaseInput
    ) -> RecordMaintenanceOperationResultUseCaseOutput:
        self.requests.append(request)
        return RecordMaintenanceOperationResultUseCaseOutput(
            run_id=request.run_id, status="running"
        )


class FakeSync(SyncDiscoveredTablesUseCase):
    def __init__(self) -> None:
        self.requests: list[SyncDiscoveredTablesUseCaseInput] = []

    def execute(
        self, request: SyncDiscoveredTablesUseCaseInput
    ) -> SyncDiscoveredTablesUseCaseOutput:
        self.requests.append(request)
        return SyncDiscoveredTablesUseCaseOutput(
            registered=1, renamed=2, dropped=3, skipped=4
        )
