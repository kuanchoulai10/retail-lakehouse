from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine

from adapter.outbound.maintenance_run.sql.maintenance_runs_sql_repo import (
    MaintenanceRunsSqlRepo,
)
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.model.maintenance_run.operation_run_status import (
    OperationRunStatus,
)
from application.domain.model.maintenance_run.trigger_type import TriggerType
from application.domain.model.managed_table.table_uuid import TableUuid
from application.exceptions import ConflictError

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def _run(run_id: str, table: str = "u1", at: datetime = NOW) -> MaintenanceRun:
    return MaintenanceRun.create(
        MaintenanceRunId(run_id),
        TableUuid(table),
        TriggerType.SCHEDULED,
        [
            MaintenanceOperation.EXPIRE_SNAPSHOTS,
            MaintenanceOperation.REWRITE_DATA_FILES,
        ],
        at,
    )


@pytest.fixture
def repo(engine: Engine) -> MaintenanceRunsSqlRepo:
    return MaintenanceRunsSqlRepo(engine)


def test_roundtrip_with_operation_details(repo: MaintenanceRunsSqlRepo):
    run = _run("r1")
    metrics = {"rewritten_data_files_count": 12}
    run.operations = (
        replace(
            run.operations[0],
            status=OperationRunStatus.SUCCEEDED,
            attempts=2,
            started_at=NOW,
            finished_at=NOW + timedelta(minutes=3),
            spark_application="app-1",
            metrics=metrics,
            expected_files=40,
        ),
        replace(run.operations[1], status=OperationRunStatus.FAILED, error="boom"),
    )
    run.finished_at = NOW + timedelta(minutes=5)
    repo.create(run)
    loaded = repo.get(MaintenanceRunId("r1"))
    assert loaded is not None
    assert loaded.table_uuid == TableUuid("u1")
    assert loaded.trigger is TriggerType.SCHEDULED
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.finished_at == NOW + timedelta(minutes=5)
    assert loaded.operations == run.operations
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


def test_get_missing_returns_none(repo: MaintenanceRunsSqlRepo):
    assert repo.get(MaintenanceRunId("nope")) is None


def test_update_persists(repo: MaintenanceRunsSqlRepo):
    run = _run("r1")
    repo.create(run)
    run.operations = (
        replace(run.operations[0], status=OperationRunStatus.RUNNING, attempts=1),
        run.operations[1],
    )
    run.finished_at = NOW + timedelta(hours=1)
    repo.update(run)
    loaded = repo.get(run.id)
    assert loaded is not None
    assert loaded.operations[0].status is OperationRunStatus.RUNNING
    assert loaded.finished_at == NOW + timedelta(hours=1)


def test_update_missing_raises(repo: MaintenanceRunsSqlRepo):
    with pytest.raises(LookupError):
        repo.update(_run("ghost"))


def test_list_by_table_newest_first_with_limit(repo: MaintenanceRunsSqlRepo):
    for i in range(5):
        repo.create(_run(f"r{i}", "u1", NOW + timedelta(minutes=i)))
    repo.create(_run("other", "u2", NOW + timedelta(hours=9)))
    got = repo.list_by_table(TableUuid("u1"))
    assert [r.id.value for r in got] == ["r4", "r3", "r2", "r1", "r0"]
    limited = repo.list_by_table(TableUuid("u1"), limit=2)
    assert [r.id.value for r in limited] == ["r4", "r3"]
    assert repo.list_by_table(TableUuid("none")) == []


def test_list_all_newest_first(repo: MaintenanceRunsSqlRepo):
    repo.create(_run("a", at=NOW))
    repo.create(_run("b", at=NOW + timedelta(minutes=1)))
    assert [r.id.value for r in repo.list_all()] == ["b", "a"]


def test_create_duplicate_primary_key_raises_conflict(repo: MaintenanceRunsSqlRepo):
    repo.create(_run("r1"))
    with pytest.raises(ConflictError):
        repo.create(_run("r1"))
