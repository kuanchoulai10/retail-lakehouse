"""Test that the callback URL the submit service builds is served by the web API."""

from __future__ import annotations

from urllib.parse import urlsplit

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    ProcessTableMaintenanceCallbackUseCaseOutput,
    SubmitMaintenanceOperationUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    SubmitMaintenanceOperationService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_runs_repo import (
    InMemoryTableMaintenanceRunsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import (
    InMemoryTablesRepo,
)
from tests.context.table_maintenance.fakes.recording_submit_maintenance_job_gateway import (
    RecordingSubmitMaintenanceJobGateway,
)


def _submitted_callback_url() -> str:
    tables = InMemoryTablesRepo()
    tables.create(
        Table.register_auto(
            TableId("u-1"),
            TableName(catalog="iceberg", namespace="sales", table="orders"),
            TableDiscoveryRuleId("r-1"),
            TableMaintenancePresetId("p-1"),
            MaintenanceSettings(),
            NOW,
        )
    )
    runs = InMemoryTableMaintenanceRunsRepo()
    runs.create(
        TableMaintenanceRun.create(
            TableMaintenanceRunId("run-1"),
            TableId("u-1"),
            TriggerType.SCHEDULED,
            [MaintenanceOperation.EXPIRE_SNAPSHOTS],
            NOW,
            execution_ref="wf-run-1",
        )
    )
    gateway = RecordingSubmitMaintenanceJobGateway()
    SubmitMaintenanceOperationService(runs, tables, gateway).execute(
        SubmitMaintenanceOperationUseCaseInput(
            run_id="run-1",
            operation="expire_snapshots",
            attempt=1,
            filters=[],
            procedure_args={},
            callback_base_url="http://api.example:8000/",
            now=NOW,
        )
    )
    (call,) = gateway.calls
    return call.callback_url


def test_callback_url_is_served_by_the_result_route():
    """Posting to the configured callback URL reaches the result route and is accepted."""
    url = urlsplit(_submitted_callback_url())
    callback = StubUseCase(ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True))
    client = build_client(process_table_maintenance_callback=callback)

    response = client.post(url.path, json={"attempt": 1, "succeeded": True})

    assert response.status_code not in (404, 405)
    assert response.status_code == 202
    (request,) = callback.requests
    assert (request.run_id, request.operation) == ("run-1", "expire_snapshots")
