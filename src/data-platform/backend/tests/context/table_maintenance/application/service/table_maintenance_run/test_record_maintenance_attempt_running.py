"""Test the service that records when an attempt's Spark driver started."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RecordMaintenanceAttemptRunningUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    RecordMaintenanceAttemptRunningService,
)

RUN_1 = "mr-00000000000000000000000001"
UNKNOWN_RUN = "mr-7zzzzzzzzzzzzzzzzzzzzzzzzz"
RDF = MaintenanceOperation.REWRITE_DATA_FILES


@pytest.fixture
def queued_run(runs_repo, now) -> TableMaintenanceRun:
    """Provide a stored run whose first attempt is queued."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_1), TableId("u-1"), TriggerType.SCHEDULED, RDF, now, execution_ref="wf-1"
    )
    run.start_attempt(1, "job-1", now, size=ComputeSize.S)
    runs_repo.create(run)
    return run


def _input(now, **overrides):
    fields = {
        "run_id": RUN_1,
        "operation": "rewrite_data_files",
        "attempt": 1,
        "started_running_at": now + timedelta(minutes=5),
        "now": now + timedelta(minutes=10),
    }
    fields.update(overrides)
    return RecordMaintenanceAttemptRunningUseCaseInput(**fields)


def test_record_running_saves_the_attempt(runs_repo, queued_run, now):
    """A queued attempt becomes running, with the driver's start as its running time."""
    out = RecordMaintenanceAttemptRunningService(runs_repo).execute(_input(now))

    assert (out.status, out.started_running_at) == ("running", now + timedelta(minutes=5))
    stored = runs_repo.get(TableMaintenanceRunId(RUN_1)).attempt_record(1)
    assert stored is not None
    assert (stored.status.value, stored.started_running_at) == ("running", now + timedelta(minutes=5))


def test_record_running_again_keeps_the_first_time(runs_repo, queued_run, now):
    """A repeated report leaves the recorded running time alone."""
    service = RecordMaintenanceAttemptRunningService(runs_repo)
    service.execute(_input(now))

    out = service.execute(_input(now, started_running_at=now + timedelta(minutes=8)))

    assert (out.status, out.started_running_at) == ("running", now + timedelta(minutes=5))


def test_record_running_clamps_a_time_before_the_submit(runs_repo, queued_run, now):
    """A driver start before the attempt was submitted is recorded as the submit time."""
    out = RecordMaintenanceAttemptRunningService(runs_repo).execute(
        _input(now, started_running_at=now - timedelta(minutes=5))
    )

    assert out.started_running_at == now


def test_record_running_of_an_unknown_run_is_not_found(runs_repo, now):
    """A run that does not exist is not found."""
    with pytest.raises(NotFoundError):
        RecordMaintenanceAttemptRunningService(runs_repo).execute(_input(now, run_id=UNKNOWN_RUN))


def test_record_running_of_an_unknown_operation_is_invalid(runs_repo, queued_run, now):
    """An operation the platform does not know is refused."""
    with pytest.raises(ValidationError):
        RecordMaintenanceAttemptRunningService(runs_repo).execute(_input(now, operation="defragment"))


def test_record_running_of_an_attempt_never_started_is_a_conflict(runs_repo, queued_run, now):
    """A report for an attempt after the current one, which was never started, is refused as a conflict."""
    with pytest.raises(ConflictError, match="never started"):
        RecordMaintenanceAttemptRunningService(runs_repo).execute(_input(now, attempt=2))


def test_record_running_of_another_operation_is_a_conflict(runs_repo, queued_run, now):
    """A report naming an operation the run does not run is refused as a conflict and changes nothing."""
    with pytest.raises(ConflictError, match=f"run {RUN_1} does not run expire_snapshots"):
        RecordMaintenanceAttemptRunningService(runs_repo).execute(_input(now, operation="expire_snapshots"))
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).status.value == "queued"
