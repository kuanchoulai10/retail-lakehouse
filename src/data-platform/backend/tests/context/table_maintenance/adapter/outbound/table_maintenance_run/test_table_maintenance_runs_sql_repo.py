"""Test the SQL repository of the TableMaintenanceRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import text

from context.table_maintenance.adapter.outbound.table_maintenance_run.sql import (
    TableMaintenanceRunRowMapper,
    TableMaintenanceRunsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    NextAttempt,
    NextStep,
    OperationRunStatus,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import ConflictError
from tests.context.table_maintenance.numbered_id import numbered_id

if TYPE_CHECKING:
    from sqlalchemy import Engine, RowMapping

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
R1 = numbered_id("mr", 1)
OTHER = numbered_id("mr", 900)
MISSING = numbered_id("mr", 999)


def _run(run_id: str, table: str = "u1", at: datetime = NOW) -> TableMaintenanceRun:
    return TableMaintenanceRun.create(
        TableMaintenanceRunId(run_id),
        TableId(table),
        TriggerType.SCHEDULED,
        [
            MaintenanceOperation.EXPIRE_SNAPSHOTS,
            MaintenanceOperation.REWRITE_DATA_FILES,
        ],
        at,
        execution_ref=f"wf-{run_id}",
    )


@pytest.fixture
def repo(engine: Engine) -> TableMaintenanceRunsSqlRepo:
    """Provide the runs repository on the test engine."""
    return TableMaintenanceRunsSqlRepo(engine)


def test_roundtrip_with_operation_details(repo: TableMaintenanceRunsSqlRepo):
    """A stored run loads back with its table, trigger and operation details."""
    run = _run(R1)
    metrics = {"rewritten_data_files_count": 12}
    run.operations = (
        run.operations[0].with_changes(
            status=OperationRunStatus.SUCCEEDED,
            attempts=2,
            started_at=NOW,
            finished_at=NOW + timedelta(minutes=3),
            job_name="app-1",
            metrics=metrics,
            expected_files=40,
        ),
        run.operations[1].with_changes(status=OperationRunStatus.FAILED, error="boom"),
    )
    run.finished_at = NOW + timedelta(minutes=5)
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.table_uuid == TableId("u1")
    assert loaded.trigger is TriggerType.SCHEDULED
    assert loaded.execution_ref == f"wf-{R1}"
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.finished_at == NOW + timedelta(minutes=5)
    assert loaded.operations == run.operations
    assert loaded.model_dump() == run.model_dump()
    first = loaded.operations[0]
    assert first.operation is MaintenanceOperation.REWRITE_DATA_FILES
    assert first.started_at == NOW
    assert first.started_at is not None
    assert first.started_at.tzinfo is not None
    assert first.metrics == metrics
    assert first.metrics is not metrics
    assert loaded.operations[1].error == "boom"
    assert loaded.status == run.status
    assert loaded.collect_events() == []


def test_priority_round_trips(repo: TableMaintenanceRunsSqlRepo):
    """A run's priority is stored and read back."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(R1),
        TableId("u1"),
        TriggerType.MANUAL,
        [MaintenanceOperation.EXPIRE_SNAPSHOTS],
        NOW,
        execution_ref=f"wf-{R1}",
        priority=TablePriority.P1,
    )
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.priority is TablePriority.P1


def test_a_row_without_a_priority_reads_as_p3(repo: TableMaintenanceRunsSqlRepo, engine: Engine):
    """A run stored before priorities existed (priority NULL) reads as the default, P3."""
    repo.create(_run(R1))
    with engine.begin() as connection:
        connection.execute(text("UPDATE table_maintenance_runs SET priority = NULL"))
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.priority is TablePriority.P3


def test_get_missing_returns_none(repo: TableMaintenanceRunsSqlRepo):
    """Getting a run that does not exist returns None."""
    assert repo.get(TableMaintenanceRunId(MISSING)) is None


def test_update_persists(repo: TableMaintenanceRunsSqlRepo):
    """An update persists the operation status and finish time."""
    run = _run(R1)
    repo.create(run)
    run.operations = (
        run.operations[0].with_changes(status=OperationRunStatus.RUNNING, attempts=1),
        run.operations[1],
    )
    run.finished_at = NOW + timedelta(hours=1)
    repo.update(run)
    loaded = repo.get(run.id)
    assert loaded is not None
    assert loaded.operations[0].status is OperationRunStatus.RUNNING
    assert loaded.finished_at == NOW + timedelta(hours=1)


def test_update_missing_raises(repo: TableMaintenanceRunsSqlRepo):
    """Updating a run that does not exist raises LookupError."""
    with pytest.raises(LookupError):
        repo.update(_run(MISSING))


def test_list_by_table_newest_first_with_limit(repo: TableMaintenanceRunsSqlRepo):
    """Runs of a table are listed newest first, cut at the limit, and empty for another table."""
    for i in range(5):
        repo.create(_run(numbered_id("mr", i), "u1", NOW + timedelta(minutes=i)))
    repo.create(_run(OTHER, "u2", NOW + timedelta(hours=9)))
    got = repo.list_by_table(TableId("u1"))
    assert [r.id.value for r in got] == [numbered_id("mr", i) for i in (4, 3, 2, 1, 0)]
    limited = repo.list_by_table(TableId("u1"), limit=2)
    assert [r.id.value for r in limited] == [numbered_id("mr", 4), numbered_id("mr", 3)]
    assert repo.list_by_table(TableId("none")) == []


def test_list_all_newest_first(repo: TableMaintenanceRunsSqlRepo):
    """Listing all runs returns the newest first."""
    first, second = numbered_id("mr", 1), numbered_id("mr", 2)
    repo.create(_run(first, at=NOW))
    repo.create(_run(second, at=NOW + timedelta(minutes=1)))
    assert [r.id.value for r in repo.list_all()] == [second, first]


def test_create_duplicate_primary_key_raises_conflict(
    repo: TableMaintenanceRunsSqlRepo,
):
    """Creating a run with an existing id raises ConflictError."""
    repo.create(_run(R1))
    with pytest.raises(ConflictError):
        repo.create(_run(R1))


def test_attempt_history_round_trips(repo: TableMaintenanceRunsSqlRepo):
    """Every attempt of an operation, with its size, class, event log state and next step, loads back."""
    run = _run(R1)
    rdf = MaintenanceOperation.REWRITE_DATA_FILES
    run.start_attempt(rdf, 1, "job-1", NOW, size=ComputeSize.S)
    run.fail(
        rdf,
        1,
        "java.lang.OutOfMemoryError",
        NOW + timedelta(minutes=1),
        failure_class=FailureClass.OOM,
        event_log_finished=False,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    run.start_attempt(rdf, 2, "job-2", NOW + timedelta(minutes=2), size=ComputeSize.M)
    run.record_attempt_running(rdf, 2, NOW + timedelta(minutes=2, seconds=30), NOW + timedelta(minutes=3))
    run.succeed(rdf, 2, {"rewritten_data_files_count": 3}, NOW + timedelta(minutes=3), event_log_finished=True)
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.operations == run.operations
    assert loaded.operations[0].attempt_history[1].started_running_at == NOW + timedelta(minutes=2, seconds=30)
    assert loaded.operations[0].attempt_history[0].started_running_at is None


def test_row_without_attempt_history_decodes_to_none_recorded():
    """A row written before attempt history existed decodes with an empty history."""
    row = {
        "id": R1,
        "table_uuid": "u1",
        "execution_ref": f"wf-{R1}",
        "trigger": "scheduled",
        "priority": None,
        "operations_json": [
            {
                "operation": "rewrite_data_files",
                "status": "failed",
                "attempts": 3,
                "started_at": NOW.isoformat(),
                "finished_at": NOW.isoformat(),
                "job_name": "job-3",
                "metrics": {},
                "error": "boom",
                "expected_files": None,
            }
        ],
        "created_at": NOW,
        "finished_at": NOW,
    }
    run = TableMaintenanceRunRowMapper.to_aggregate(cast("RowMapping", row))
    assert run.operations[0].attempt_history == ()
    assert run.operations[0].attempts == 3


def test_attempt_without_a_running_time_decodes_to_none():
    """An attempt recorded without the started_running_at key decodes with no running time."""
    row = {
        "id": R1,
        "table_uuid": "u1",
        "execution_ref": f"wf-{R1}",
        "trigger": "scheduled",
        "priority": "P3",
        "operations_json": [
            {
                "operation": "rewrite_data_files",
                "status": "running",
                "attempts": 1,
                "started_at": NOW.isoformat(),
                "finished_at": None,
                "job_name": "job-1",
                "metrics": {},
                "error": None,
                "expected_files": None,
                "attempt_history": [
                    {"attempt": 1, "size": "S", "status": "running", "started_at": NOW.isoformat()},
                ],
            }
        ],
        "created_at": NOW,
        "finished_at": None,
    }
    run = TableMaintenanceRunRowMapper.to_aggregate(cast("RowMapping", row))
    assert run.operations[0].attempt_history[0].started_running_at is None
