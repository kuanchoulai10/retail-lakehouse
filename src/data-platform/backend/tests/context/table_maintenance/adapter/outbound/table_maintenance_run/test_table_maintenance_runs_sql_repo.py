"""Test the SQL repository of the TableMaintenanceRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_run.sql import (
    TableMaintenanceRunRowMapper,
    TableMaintenanceRunsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
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

if TYPE_CHECKING:
    from sqlalchemy import Engine, RowMapping

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


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
    run = _run("r1")
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
    loaded = repo.get(TableMaintenanceRunId("r1"))
    assert loaded is not None
    assert loaded.table_uuid == TableId("u1")
    assert loaded.trigger is TriggerType.SCHEDULED
    assert loaded.execution_ref == "wf-r1"
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


def test_get_missing_returns_none(repo: TableMaintenanceRunsSqlRepo):
    """Getting a run that does not exist returns None."""
    assert repo.get(TableMaintenanceRunId("nope")) is None


def test_update_persists(repo: TableMaintenanceRunsSqlRepo):
    """An update persists the operation status and finish time."""
    run = _run("r1")
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
        repo.update(_run("ghost"))


def test_list_by_table_newest_first_with_limit(repo: TableMaintenanceRunsSqlRepo):
    """Runs of a table are listed newest first, cut at the limit, and empty for another table."""
    for i in range(5):
        repo.create(_run(f"r{i}", "u1", NOW + timedelta(minutes=i)))
    repo.create(_run("other", "u2", NOW + timedelta(hours=9)))
    got = repo.list_by_table(TableId("u1"))
    assert [r.id.value for r in got] == ["r4", "r3", "r2", "r1", "r0"]
    limited = repo.list_by_table(TableId("u1"), limit=2)
    assert [r.id.value for r in limited] == ["r4", "r3"]
    assert repo.list_by_table(TableId("none")) == []


def test_list_all_newest_first(repo: TableMaintenanceRunsSqlRepo):
    """Listing all runs returns the newest first."""
    repo.create(_run("a", at=NOW))
    repo.create(_run("b", at=NOW + timedelta(minutes=1)))
    assert [r.id.value for r in repo.list_all()] == ["b", "a"]


def test_create_duplicate_primary_key_raises_conflict(
    repo: TableMaintenanceRunsSqlRepo,
):
    """Creating a run with an existing id raises ConflictError."""
    repo.create(_run("r1"))
    with pytest.raises(ConflictError):
        repo.create(_run("r1"))


def test_list_by_table_since_filters_by_created_at(repo: TableMaintenanceRunsSqlRepo):
    """Listing runs of a table since a time keeps the runs created at or after it."""
    since = NOW - timedelta(days=30)
    repo.create(_run("old", "u1", since - timedelta(seconds=1)))
    repo.create(_run("edge", "u1", since))
    repo.create(_run("new", "u1", NOW))
    repo.create(_run("other", "u2", NOW))
    got = repo.list_by_table_since(TableId("u1"), since)
    assert [r.id.value for r in got] == ["new", "edge"]


def test_attempt_history_round_trips(repo: TableMaintenanceRunsSqlRepo):
    """Every attempt of an operation, with its size, class, event log state and next step, loads back."""
    run = _run("r-attempts")
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
    run.succeed(rdf, 2, {"rewritten_data_files_count": 3}, NOW + timedelta(minutes=3), event_log_finished=True)
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId("r-attempts"))
    assert loaded is not None
    assert loaded.operations == run.operations


def test_row_without_attempt_history_decodes_to_none_recorded():
    """A row written before attempt history existed decodes with an empty history."""
    row = {
        "id": "r-old",
        "table_uuid": "u1",
        "execution_ref": "wf-r-old",
        "trigger": "scheduled",
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
