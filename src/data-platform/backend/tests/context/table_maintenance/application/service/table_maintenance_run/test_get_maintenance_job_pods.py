"""Test the service that reports the live pods of one maintenance attempt."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobPodsUseCaseInput,
    GetMaintenanceJobPodsUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetMaintenanceJobPodsService,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_pods_gateway import (
    ScriptedReadMaintenanceJobPodsGateway,
)

RUN_1 = "mr-00000000000000000000000001"


def test_get_job_pods_returns_the_live_pods_of_the_attempt():
    """The service asks the gateway for the attempt's pods and returns the live ones."""
    pods = ScriptedReadMaintenanceJobPodsGateway()
    pods.set_live_pods(RUN_1, "rewrite_data_files", 2, "driver", "exec-1")

    out = GetMaintenanceJobPodsService(pods).execute(
        GetMaintenanceJobPodsUseCaseInput(run_id=RUN_1, operation="rewrite_data_files", attempt=2)
    )

    assert out == GetMaintenanceJobPodsUseCaseOutput(live_pods=("driver", "exec-1"))
    assert [(c.run_id, c.operation, c.attempt) for c in pods.calls] == [(RUN_1, "rewrite_data_files", 2)]


def test_get_job_pods_with_no_live_pod_is_empty():
    """An attempt without live pods reports none."""
    out = GetMaintenanceJobPodsService(ScriptedReadMaintenanceJobPodsGateway()).execute(
        GetMaintenanceJobPodsUseCaseInput(run_id=RUN_1, operation="expire_snapshots", attempt=1)
    )

    assert out.live_pods == ()


@pytest.mark.parametrize(("operation", "attempt"), [("nope", 1), ("expire_snapshots", 0)])
def test_get_job_pods_rejects_invalid_operation_or_attempt(operation, attempt):
    """An invalid operation or attempt is rejected before the gateway is called."""
    pods = ScriptedReadMaintenanceJobPodsGateway()

    with pytest.raises(ValidationError):
        GetMaintenanceJobPodsService(pods).execute(
            GetMaintenanceJobPodsUseCaseInput(run_id=RUN_1, operation=operation, attempt=attempt)
        )
    assert pods.calls == []
