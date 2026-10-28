"""Test the maintenance run lifecycle services."""

from __future__ import annotations

from datetime import timedelta

import pytest

from application.domain.model.table_discovery_rule.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.table_maintenance_run.table_maintenance_run import (
    TableMaintenanceRun,
)
from application.domain.model.table_maintenance_run.table_maintenance_run_id import (
    TableMaintenanceRunId,
)
from application.domain.model.table_maintenance_run.trigger_type import TriggerType
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.table.table import Table
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_id import TableId
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table_maintenance_run.create_table_maintenance_run import (
    CreateTableMaintenanceRunUseCaseInput,
)
from application.port.inbound.table_maintenance_run.get_table_maintenance_run import (
    GetTableMaintenanceRunUseCaseInput,
)
from application.port.inbound.table_maintenance_run.list_table_maintenance_runs import (
    ListTableMaintenanceRunsUseCaseInput,
)
from application.port.inbound.table_maintenance_run.process_table_maintenance_callback import (
    ProcessTableMaintenanceCallbackUseCaseInput,
)
from application.port.inbound.table_maintenance_run.record_table_maintenance_operation_result import (
    RecordTableMaintenanceOperationResultUseCaseInput,
)
from application.service.table_maintenance_run.create_table_maintenance_run import (
    CreateTableMaintenanceRunService,
)
from application.service.table_maintenance_run.get_table_maintenance_run import (
    GetTableMaintenanceRunService,
)
from application.service.table_maintenance_run.list_table_maintenance_runs import (
    ListTableMaintenanceRunsService,
)
from application.service.table_maintenance_run.process_table_maintenance_callback import (
    ProcessTableMaintenanceCallbackService,
)
from application.service.table_maintenance_run.record_table_maintenance_operation_result import (
    RecordTableMaintenanceOperationResultService,
)
from tests.fakes.track_calls import track_calls

OPS = MaintenanceOperation
RDF = OPS.REWRITE_DATA_FILES


@pytest.fixture
def table(tables_repo, now):
    t = Table.register_auto(
        TableId("u-1"),
        TableName("iceberg", "sales", "orders"),
        TableDiscoveryRuleId("r-1"),
        TableMaintenancePresetId("t-1"),
        MaintenanceSettings(),
        now,
    )
    tables_repo.create(t)
    return t


def _create_input(now, run_id="run-1", **overrides):
    fields = {
        "run_id": run_id,
        "table_uuid": "u-1",
        "trigger": "scheduled",
        "operations": ["expire_snapshots", "rewrite_data_files"],
        "execution_ref": "wf-run-1",
        "now": now,
    }
    fields.update(overrides)
    return CreateTableMaintenanceRunUseCaseInput(**fields)


@pytest.fixture
def creator(runs_repo, tables_repo):
    return CreateTableMaintenanceRunService(runs_repo, tables_repo)


def test_create_run_persists_pending_run_in_canonical_order(
    creator, runs_repo, table, now
):
    out = creator.execute(_create_input(now))
    assert (out.run_id, out.table_uuid, out.trigger) == ("run-1", "u-1", "scheduled")
    assert out.execution_ref == "wf-run-1"
    assert runs_repo.get(TableMaintenanceRunId("run-1")).execution_ref == "wf-run-1"
    assert out.status == "pending"
    assert [o["operation"] for o in out.operations] == [
        "rewrite_data_files",
        "expire_snapshots",
    ]
    assert out.operations[0]["status"] == "pending"
    assert out.created_at == now
    assert runs_repo.get(TableMaintenanceRunId("run-1")) is not None


def test_create_run_is_idempotent_by_id(creator, runs_repo, table, now):
    creator.execute(_create_input(now))
    run = runs_repo.get(TableMaintenanceRunId("run-1"))
    run.start_attempt(RDF, 1, "app-1", now)
    again = creator.execute(_create_input(now + timedelta(hours=1), trigger="manual"))
    assert again.trigger == "scheduled"
    assert again.status == "running"
    assert again.created_at == now
    assert len(runs_repo.items) == 1


def test_create_run_validates_input(creator, table, now):
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, trigger="whenever"))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, operations=["defragment"]))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, operations=[]))
    with pytest.raises(ValidationError):
        creator.execute(_create_input(now, execution_ref=""))
    with pytest.raises(NotFoundError):
        creator.execute(_create_input(now, table_uuid="missing"))


# --- record result ---


@pytest.fixture
def started_run(runs_repo, table, now):
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId("run-1"),
        table.id,
        TriggerType.SCHEDULED,
        [RDF, OPS.EXPIRE_SNAPSHOTS],
        now,
        execution_ref="wf-run-1",
    )
    run.start_attempt(RDF, 1, "tm-rdf-run1-a1", now)
    runs_repo.create(run)
    return run


@pytest.fixture
def recorder(runs_repo, tables_repo):
    return RecordTableMaintenanceOperationResultService(runs_repo, tables_repo)


def _record(recorder, now, **overrides):
    fields = {
        "run_id": "run-1",
        "operation": "rewrite_data_files",
        "attempt": 1,
        "succeeded": True,
        "metrics": {"rewritten_files": 4},
        "error": None,
        "now": now,
    }
    fields.update(overrides)
    return recorder.execute(RecordTableMaintenanceOperationResultUseCaseInput(**fields))


def test_record_result_updates_run_and_table_backoff(recorder, started_run, table, now):
    later = now + timedelta(minutes=5)
    out = _record(recorder, later, succeeded=False, error="OOM")
    assert (out.run_id, out.status) == ("run-1", "running")
    op = started_run.operations[0]
    assert (op.status.value, op.error, op.finished_at) == ("failed", "OOM", later)
    state = table.operation_state(RDF)
    assert (state.consecutive_failures, state.last_attempt_at) == (1, later)


def test_record_success_stores_metrics_and_resets_backoff(
    recorder, started_run, table, now
):
    table.record_operation_result(RDF, False, now)
    _record(recorder, now)
    assert started_run.operations[0].metrics == {"rewritten_files": 4}
    assert table.operation_state(RDF).consecutive_failures == 0


def test_record_result_saves_run_then_table(
    recorder, started_run, table, runs_repo, tables_repo, log, now
):
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    _record(recorder, now)
    assert log == [("runs.update", "run-1"), ("tables.update", "u-1")]


def test_record_result_stale_attempt_is_ignored(recorder, started_run, table, now):
    started_run.fail(RDF, 1, "boom", now)
    started_run.start_attempt(RDF, 2, "tm-rdf-run1-a2", now)
    out = _record(recorder, now, attempt=1, succeeded=False, error="late")
    assert out.status == "running"
    assert started_run.operations[0].status.value == "running"
    assert table.operation_state(RDF).consecutive_failures == 0


def test_record_result_replay_does_not_count_twice(recorder, started_run, table, now):
    _record(recorder, now, succeeded=False, error="OOM")
    _record(recorder, now, succeeded=False, error="OOM")
    assert table.operation_state(RDF).consecutive_failures == 1


def test_record_result_failure_without_error_gets_a_default(
    recorder, started_run, table, now
):
    _record(recorder, now, succeeded=False, error=None)
    assert started_run.operations[0].error == "unknown error"


def test_record_result_for_dropped_table_still_updates_run(
    recorder, started_run, table, now
):
    table.mark_dropped(now)
    out = _record(recorder, now)
    assert started_run.operations[0].status.value == "succeeded"
    assert out.status == "running"
    assert table.operation_states == {}


def test_record_result_final_operation_finishes_run(recorder, started_run, table, now):
    _record(recorder, now)
    started_run.start_attempt(OPS.EXPIRE_SNAPSHOTS, 1, "tm-es-run1-a1", now)
    out = _record(recorder, now, operation="expire_snapshots")
    assert out.status == "succeeded"


def test_record_result_rejects_bad_requests(recorder, started_run, now):
    with pytest.raises(NotFoundError):
        _record(recorder, now, run_id="nope")
    with pytest.raises(ValidationError):
        _record(recorder, now, operation="defragment")
    with pytest.raises(ConflictError, match="not part of"):
        _record(recorder, now, operation="remove_orphan_files")
    with pytest.raises(ConflictError, match="never started"):
        _record(recorder, now, attempt=2)


# --- callback ---


def test_callback_forwards_result_to_the_workflow(runs_repo, started_run, results):
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
    out = service.execute(
        ProcessTableMaintenanceCallbackUseCaseInput(
            "run-1", "rewrite_data_files", 3, False, {"a": 1}, "OOM"
        )
    )
    assert out.accepted is True
    (call,) = results.calls
    assert (call.run_id, call.operation, call.attempt) == (
        "run-1",
        "rewrite_data_files",
        3,
    )
    assert (call.succeeded, call.metrics, call.error) == (False, {"a": 1}, "OOM")
    assert call.execution_ref == "wf-run-1"


def test_callback_unknown_run_not_found(runs_repo, results):
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
    with pytest.raises(NotFoundError):
        service.execute(
            ProcessTableMaintenanceCallbackUseCaseInput(
                "nope", "rewrite_data_files", 1, True, {}, None
            )
        )
    assert results.calls == []


def test_callback_rejects_unknown_operation(runs_repo, started_run, results):
    service = ProcessTableMaintenanceCallbackService(runs_repo, results)
    with pytest.raises(ValidationError):
        service.execute(
            ProcessTableMaintenanceCallbackUseCaseInput("run-1", "x", 1, True, {}, None)
        )


# --- get / list ---


def test_get_run_returns_the_run_or_not_found(runs_repo, started_run):
    service = GetTableMaintenanceRunService(runs_repo)
    out = service.execute(GetTableMaintenanceRunUseCaseInput("run-1"))
    assert out.status == "running"
    assert out.operations[0]["job_name"] == "tm-rdf-run1-a1"
    with pytest.raises(NotFoundError):
        service.execute(GetTableMaintenanceRunUseCaseInput("nope"))


def test_list_runs_newest_first_with_limit(runs_repo, table, now):
    for i in range(3):
        runs_repo.create(
            TableMaintenanceRun.create(
                TableMaintenanceRunId(f"run-{i}"),
                table.id,
                TriggerType.MANUAL,
                [RDF],
                now + timedelta(minutes=i),
                execution_ref=f"wf-run-{i}",
            )
        )
    service = ListTableMaintenanceRunsService(runs_repo)
    out = service.execute(ListTableMaintenanceRunsUseCaseInput("u-1"))
    assert [i.run_id for i in out.items] == ["run-2", "run-1", "run-0"]
    limited = service.execute(ListTableMaintenanceRunsUseCaseInput("u-1", limit=1))
    assert [i.run_id for i in limited.items] == ["run-2"]
    assert service.execute(ListTableMaintenanceRunsUseCaseInput("other")).items == []
