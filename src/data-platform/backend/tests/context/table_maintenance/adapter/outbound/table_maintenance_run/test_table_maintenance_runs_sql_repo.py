"""Test the SQL repository of the TableMaintenanceRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import text

from base import InvariantViolation
from context.table_maintenance.adapter.outbound.table_maintenance_run.sql import (
    TableMaintenanceRunRowMapper,
    TableMaintenanceRunsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    SpecFilter,
    TablePriority,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    NextAttempt,
    NextStep,
    RunStatus,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunsUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    CreateTableMaintenanceRunsService,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.numbered_id import numbered_id

if TYPE_CHECKING:
    from sqlalchemy import Engine, RowMapping

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
R1 = numbered_id("mr", 1)
OTHER = numbered_id("mr", 900)
MISSING = numbered_id("mr", 999)


def _run(
    run_id: str, table: str = "u1", at: datetime = NOW, *, operation: Op = Op.EXPIRE_SNAPSHOTS
) -> TableMaintenanceRun:
    return TableMaintenanceRun.create(
        TableMaintenanceRunId(run_id),
        TableId(table),
        TriggerType.SCHEDULED,
        operation,
        at,
        execution_ref=f"wf-{run_id}",
    )


@pytest.fixture
def repo(engine: Engine) -> TableMaintenanceRunsSqlRepo:
    """Provide the runs repository on the test engine."""
    return TableMaintenanceRunsSqlRepo(engine)


def test_sql_round_trip_keeps_every_field(repo: TableMaintenanceRunsSqlRepo):
    """A stored run loads back equal, with its operation, filters, arguments, metrics and attempts."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(R1),
        TableId("u1"),
        TriggerType.SCHEDULED,
        Op.REWRITE_DATA_FILES,
        NOW,
        execution_ref="wf",
        filters=[SpecFilter(spec_id=0, where="(`region` = 'eu')")],
        procedure_args={"options": {"min-input-files": "2"}},
    )
    run.start_attempt(1, "job-1", NOW, size=ComputeSize.S)
    run.succeed(1, {"rewritten_data_files_count": 4}, NOW, started_running_at=NOW, event_log_finished=True)
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded == run
    assert loaded is not None
    assert loaded.model_dump() == run.model_dump()
    assert loaded.created_at.tzinfo is not None
    assert loaded.collect_events() == []


def test_a_skipped_run_round_trips_its_reason(repo: TableMaintenanceRunsSqlRepo):
    """A skipped run loads back skipped, with why and when."""
    run = _run(R1)
    run.skip("the table's maintenance stopped before this run started", NOW + timedelta(minutes=1))
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded == run
    assert loaded is not None
    assert loaded.model_dump() == run.model_dump()
    assert loaded.skip_reason == "the table's maintenance stopped before this run started"
    assert loaded.finished_at == NOW + timedelta(minutes=1)


def test_priority_round_trips(repo: TableMaintenanceRunsSqlRepo):
    """A run's priority is stored and read back."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(R1),
        TableId("u1"),
        TriggerType.MANUAL,
        Op.EXPIRE_SNAPSHOTS,
        NOW,
        execution_ref=f"wf-{R1}",
        priority=TablePriority.P1,
    )
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.priority is TablePriority.P1


def test_a_row_without_a_priority_reads_as_p3(repo: TableMaintenanceRunsSqlRepo, engine: Engine):
    """A run stored without a priority (priority NULL) reads as the default, P3."""
    repo.create(_run(R1))
    with engine.begin() as connection:
        connection.execute(text("UPDATE table_maintenance_runs SET priority = NULL"))
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.priority is TablePriority.P3


def test_the_status_is_a_column(repo: TableMaintenanceRunsSqlRepo, engine: Engine):
    """The run's status and operation are real columns, not buried in JSON."""
    repo.create(_run(R1))
    with engine.connect() as conn:
        assert conn.execute(text("select status, operation from table_maintenance_runs")).one() == (
            "pending",
            "expire_snapshots",
        )


def test_get_missing_returns_none(repo: TableMaintenanceRunsSqlRepo):
    """Getting a run that does not exist returns None."""
    assert repo.get(TableMaintenanceRunId(MISSING)) is None


def test_update_persists(repo: TableMaintenanceRunsSqlRepo):
    """An update persists the status, the attempts and the finish time."""
    run = _run(R1)
    repo.create(run)
    run.start_attempt(1, "job-1", NOW, size=ComputeSize.S)
    run.fail(1, "boom", NOW + timedelta(hours=1))
    repo.update(run)
    loaded = repo.get(run.id)
    assert loaded is not None
    assert loaded.status is RunStatus.FAILED
    assert loaded.error == "boom"
    assert loaded.finished_at == NOW + timedelta(hours=1)
    assert loaded.attempts == run.attempts


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


def test_runs_created_together_list_the_last_operation_first(repo: TableMaintenanceRunsSqlRepo):
    """The runs a plan created at one time list the plan's last operation first."""
    ops = [Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS, Op.REMOVE_ORPHAN_FILES]
    for n, op in enumerate(ops, start=1):
        repo.create(_run(numbered_id("mr", n), operation=op))
    listed = repo.list_by_table(TableId("u1"))
    assert [r.operation for r in listed] == list(reversed(ops))


def test_runs_of_one_time_and_operation_list_the_larger_id_first(repo: TableMaintenanceRunsSqlRepo):
    """Two runs of one time and one operation list by id, the larger first."""
    repo.create(_run(numbered_id("mr", 1)))
    repo.create(_run(numbered_id("mr", 2)))
    assert [r.id.value for r in repo.list_by_table(TableId("u1"))] == [numbered_id("mr", 2), numbered_id("mr", 1)]


def test_list_all_newest_first(repo: TableMaintenanceRunsSqlRepo):
    """Listing all runs returns the newest first."""
    first, second = numbered_id("mr", 1), numbered_id("mr", 2)
    repo.create(_run(first, at=NOW))
    repo.create(_run(second, at=NOW + timedelta(minutes=1)))
    assert [r.id.value for r in repo.list_all()] == [second, first]


def test_list_all_orders_runs_created_together_as_the_table_listing_does(repo: TableMaintenanceRunsSqlRepo):
    """Among runs of one creation time, every run lists by the plan's operation order before its id."""
    repo.create(_run(numbered_id("mr", 3), operation=Op.REWRITE_DATA_FILES))
    repo.create(_run(numbered_id("mr", 1), operation=Op.REMOVE_ORPHAN_FILES))
    repo.create(_run(numbered_id("mr", 2), table="u2", operation=Op.REMOVE_ORPHAN_FILES))
    assert [r.id.value for r in repo.list_all()] == [numbered_id("mr", n) for n in (2, 1, 3)]


def test_create_duplicate_primary_key_raises_conflict(
    repo: TableMaintenanceRunsSqlRepo,
):
    """Creating a run with an existing id raises ConflictError."""
    repo.create(_run(R1))
    with pytest.raises(ConflictError):
        repo.create(_run(R1))


def test_create_all_stores_every_run(repo: TableMaintenanceRunsSqlRepo):
    """The runs of one plan are stored together and read back."""
    ops = [Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS]
    runs = [_run(numbered_id("mr", n), operation=op) for n, op in enumerate(ops, start=1)]
    assert repo.create_all(runs) == runs
    assert [repo.get(r.id) for r in runs] == runs


def test_create_all_stores_none_when_one_cannot_be_stored(repo: TableMaintenanceRunsSqlRepo):
    """A run that cannot be stored refuses the whole batch with ConflictError: the runs before it are not stored."""
    repo.create(_run(OTHER))
    with pytest.raises(ConflictError):
        repo.create_all([_run(R1, operation=Op.REWRITE_DATA_FILES), _run(OTHER)])
    assert repo.get(TableMaintenanceRunId(R1)) is None
    assert [r.id.value for r in repo.list_all()] == [OTHER]


def test_a_create_of_a_plan_retried_after_it_was_stored_succeeds_on_the_sql_repo(repo: TableMaintenanceRunsSqlRepo):
    """The create use case, retried after its first try committed the plan's runs here, returns the stored runs.

    The idempotency lives in the use case: it reads each run id back from this repo before inserting.
    """
    tables = InMemoryTablesRepo()
    tables.create(
        Table.register(
            TableId("u1"), TableName(catalog="iceberg", namespace="s", table="t"), TableDiscoveryRuleId.new(), NOW
        )
    )
    service = CreateTableMaintenanceRunsService(repo, tables)
    request = CreateTableMaintenanceRunsUseCaseInput(
        table_uuid="u1",
        execution_ref="wf",
        trigger="scheduled",
        now=NOW,
        runs=(
            CreateTableMaintenanceRunsUseCaseInput.Run(run_id=R1, operation="rewrite_data_files"),
            CreateTableMaintenanceRunsUseCaseInput.Run(run_id=OTHER, operation="expire_snapshots"),
        ),
    )
    first = service.execute(request)
    again = service.execute(request)
    assert again.run_ids == first.run_ids == (R1, OTHER)
    assert sorted(r.id.value for r in repo.list_all()) == sorted([R1, OTHER])


def test_attempts_round_trip(repo: TableMaintenanceRunsSqlRepo):
    """Every attempt, with its job, size, class, event log state and next step, loads back."""
    run = _run(R1, operation=Op.REWRITE_DATA_FILES)
    run.start_attempt(1, "job-1", NOW, size=ComputeSize.S)
    run.fail(
        1,
        "java.lang.OutOfMemoryError",
        NOW + timedelta(minutes=1),
        failure_class=FailureClass.OOM,
        event_log_finished=False,
        next_attempt=NextAttempt(step=NextStep.RETRY_LARGER, size=ComputeSize.M),
    )
    run.start_attempt(2, "job-2", NOW + timedelta(minutes=2), size=ComputeSize.M)
    run.record_attempt_running(2, NOW + timedelta(minutes=2, seconds=30), NOW + timedelta(minutes=3))
    run.succeed(2, {"rewritten_data_files_count": 3}, NOW + timedelta(minutes=3), event_log_finished=True)
    repo.create(run)
    loaded = repo.get(TableMaintenanceRunId(R1))
    assert loaded is not None
    assert loaded.attempts == run.attempts
    assert [a.job_name for a in loaded.attempts] == ["job-1", "job-2"]
    assert loaded.attempts[1].started_running_at == NOW + timedelta(minutes=2, seconds=30)
    assert loaded.attempts[0].started_running_at is None


def test_attempt_without_a_running_time_decodes_to_none():
    """An attempt recorded without the started_running_at or job_name key decodes with neither."""
    row = {
        "id": R1,
        "table_uuid": "u1",
        "execution_ref": f"wf-{R1}",
        "trigger": "scheduled",
        "operation": "rewrite_data_files",
        "priority": "P3",
        "status": "running",
        "error": None,
        "skip_reason": None,
        "filters_json": [],
        "procedure_args_json": {},
        "metrics_json": {},
        "attempts_json": [
            {"attempt": 1, "size": "S", "status": "running", "started_at": NOW.isoformat()},
        ],
        "created_at": NOW,
        "finished_at": None,
    }
    run = TableMaintenanceRunRowMapper.to_aggregate(cast("RowMapping", row))
    assert run.attempts[0].started_running_at is None
    assert run.attempts[0].job_name is None


def test_among_runs_created_together_the_operation_outranks_the_id(repo: TableMaintenanceRunsSqlRepo):
    """Runs of one creation time list by the plan's operation order before their ids."""
    repo.create(_run(numbered_id("mr", 2), operation=Op.REWRITE_DATA_FILES))
    repo.create(_run(numbered_id("mr", 1), operation=Op.REMOVE_ORPHAN_FILES))
    listed = repo.list_by_table(TableId("u1"))
    assert [r.operation for r in listed] == [Op.REMOVE_ORPHAN_FILES, Op.REWRITE_DATA_FILES]


def test_a_status_that_disagrees_with_the_attempts_is_refused_on_load():
    """A row whose status column is not its latest attempt's status does not load."""
    row = {
        "id": R1,
        "table_uuid": "u1",
        "execution_ref": f"wf-{R1}",
        "trigger": "scheduled",
        "operation": "expire_snapshots",
        "priority": "P3",
        "status": "succeeded",
        "error": None,
        "skip_reason": None,
        "filters_json": [],
        "procedure_args_json": {},
        "metrics_json": {},
        "attempts_json": [
            {"attempt": 1, "size": "S", "status": "queued", "started_at": NOW.isoformat()},
        ],
        "created_at": NOW,
        "finished_at": NOW,
    }
    with pytest.raises(InvariantViolation, match="latest attempt's status"):
        TableMaintenanceRunRowMapper.to_aggregate(cast("RowMapping", row))
