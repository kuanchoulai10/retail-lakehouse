"""Provide the table_maintenance_activities_with_fakes test builder."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableMaintenanceActivities,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetMaintenanceJobPodsService,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    FakeCreateRun,
    FakeDelete,
    FakeRecordResult,
    FakeRecordRunning,
    FakeStatus,
    FakeSubmit,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_pods_gateway import (
    ScriptedReadMaintenanceJobPodsGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CreateTableMaintenanceRunUseCase,
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobPodsUseCase,
        GetMaintenanceJobStatusUseCase,
        RecordMaintenanceAttemptRunningUseCase,
        RecordTableMaintenanceOperationResultUseCase,
        SubmitMaintenanceOperationUseCase,
    )


def table_maintenance_activities_with_fakes(  # noqa: PLR0913
    *,
    create_run: CreateTableMaintenanceRunUseCase | None = None,
    record_result: RecordTableMaintenanceOperationResultUseCase | None = None,
    submit: SubmitMaintenanceOperationUseCase | None = None,
    status: GetMaintenanceJobStatusUseCase | None = None,
    delete: DeleteMaintenanceJobUseCase | None = None,
    pods: GetMaintenanceJobPodsUseCase | None = None,
    record_running: RecordMaintenanceAttemptRunningUseCase | None = None,
    client: Client | None = None,
    callback_base_url: str = "http://cp:8000",
) -> TableMaintenanceActivities:
    """Build the maintenance activities, a recording fake for every use case and a mock client not given."""
    return TableMaintenanceActivities(
        create_run=create_run or FakeCreateRun(),
        record_result=record_result or FakeRecordResult(),
        submit=submit or FakeSubmit(),
        status=status or FakeStatus(),
        delete=delete or FakeDelete(),
        pods=pods or GetMaintenanceJobPodsService(ScriptedReadMaintenanceJobPodsGateway()),
        record_running=record_running or FakeRecordRunning(),
        client=client or MagicMock(),
        callback_base_url=callback_base_url,
    )
