"""Test the service that reports the live pods of one maintenance attempt."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableId,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRun, TriggerType
from context.table_maintenance.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobProcessesUseCaseInput,
    GetMaintenanceJobProcessesUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetMaintenanceJobProcessesService,
)
from tests.context.table_maintenance.fakes.job_content import job_content
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_processes_gateway import (
    ScriptedReadMaintenanceJobProcessesGateway,
)

RUN_1 = "mr-00000000000000000000000001"
UNKNOWN_RUN = "mr-7zzzzzzzzzzzzzzzzzzzzzzzzz"


@pytest.fixture(autouse=True)
def run(runs_repo, now):
    """Provide a stored compaction run."""
    created = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_1),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        MaintenanceOperation.REWRITE_DATA_FILES,
        now,
        content=job_content(MaintenanceOperation.REWRITE_DATA_FILES),
        execution_ref="wf-run-1",
    )
    runs_repo.create(created)
    return created


def _input(run_id=RUN_1, operation="rewrite_data_files", attempt=1):
    return GetMaintenanceJobProcessesUseCaseInput(run_id=run_id, operation=operation, attempt=attempt)


def test_get_job_pods_returns_the_live_pods_of_the_attempt(runs_repo):
    """The service asks the gateway for the attempt's pods and returns the live ones."""
    pods = ScriptedReadMaintenanceJobProcessesGateway()
    pods.set_live_processes(RUN_1, "rewrite_data_files", 2, "driver", "exec-1")

    out = GetMaintenanceJobProcessesService(runs_repo, pods).execute(_input(attempt=2))

    assert out == GetMaintenanceJobProcessesUseCaseOutput(live_processes=("driver", "exec-1"))
    assert [(c.run_id, c.operation, c.attempt) for c in pods.calls] == [(RUN_1, "rewrite_data_files", 2)]


def test_get_job_pods_with_no_live_pod_is_empty(runs_repo):
    """An attempt without live pods reports none."""
    out = GetMaintenanceJobProcessesService(runs_repo, ScriptedReadMaintenanceJobProcessesGateway()).execute(_input())

    assert out.live_processes == ()


@pytest.mark.parametrize(("operation", "attempt"), [("nope", 1), ("rewrite_data_files", 0)])
def test_get_job_pods_rejects_invalid_operation_or_attempt(runs_repo, operation, attempt):
    """An invalid operation or attempt is rejected before the gateway is called."""
    pods = ScriptedReadMaintenanceJobProcessesGateway()

    with pytest.raises(ValidationError):
        GetMaintenanceJobProcessesService(runs_repo, pods).execute(_input(operation=operation, attempt=attempt))
    assert pods.calls == []


def test_get_job_pods_refuses_another_operation(runs_repo):
    """A pods read naming an operation the run does not run is a conflict and reads nothing."""
    pods = ScriptedReadMaintenanceJobProcessesGateway()

    with pytest.raises(ConflictError, match=f"run {RUN_1} does not run expire_snapshots"):
        GetMaintenanceJobProcessesService(runs_repo, pods).execute(_input(operation="expire_snapshots"))
    assert pods.calls == []


def test_get_job_pods_of_an_unknown_run_is_not_found(runs_repo):
    """A pods read for a run that does not exist raises NotFoundError and reads nothing."""
    pods = ScriptedReadMaintenanceJobProcessesGateway()

    with pytest.raises(NotFoundError):
        GetMaintenanceJobProcessesService(runs_repo, pods).execute(_input(run_id=UNKNOWN_RUN))
    assert pods.calls == []
