"""Provide the table_maintenance_activities_with_fakes test builder."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableMaintenanceActivities,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetMaintenanceJobProcessesService,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.runs_repo_with_one_run import (
    runs_repo_with_one_run,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    FakeDelete,
    FakeRaisePriority,
    FakeRecordResult,
    FakeRecordRunning,
    FakeSkip,
    FakeStatus,
    FakeSubmit,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_processes_gateway import (
    ScriptedReadMaintenanceJobProcessesGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobProcessesUseCase,
        GetMaintenanceJobStatusUseCase,
        RaiseTableMaintenanceRunPriorityUseCase,
        RecordMaintenanceAttemptRunningUseCase,
        RecordTableMaintenanceOperationResultUseCase,
        SkipTableMaintenanceRunUseCase,
        SubmitMaintenanceOperationUseCase,
    )


def table_maintenance_activities_with_fakes(  # noqa: PLR0913
    *,
    record_result: RecordTableMaintenanceOperationResultUseCase | None = None,
    submit: SubmitMaintenanceOperationUseCase | None = None,
    status: GetMaintenanceJobStatusUseCase | None = None,
    delete: DeleteMaintenanceJobUseCase | None = None,
    pods: GetMaintenanceJobProcessesUseCase | None = None,
    record_running: RecordMaintenanceAttemptRunningUseCase | None = None,
    raise_priority: RaiseTableMaintenanceRunPriorityUseCase | None = None,
    skip: SkipTableMaintenanceRunUseCase | None = None,
    client: Client | None = None,
    callback_base_url: str = "http://cp:8000",
) -> TableMaintenanceActivities:
    """Build the maintenance activities, a recording fake for every use case and a mock client not given.

    The pods use case defaults to the real service over a stored compaction run with no live pods.
    """
    return TableMaintenanceActivities(
        record_result=record_result or FakeRecordResult(),
        submit=submit or FakeSubmit(),
        status=status or FakeStatus(),
        delete=delete or FakeDelete(),
        pods=pods
        or GetMaintenanceJobProcessesService(runs_repo_with_one_run(), ScriptedReadMaintenanceJobProcessesGateway()),
        record_running=record_running or FakeRecordRunning(),
        raise_priority=raise_priority or FakeRaisePriority(),
        skip=skip or FakeSkip(),
        client=client or MagicMock(),
        callback_base_url=callback_base_url,
    )
