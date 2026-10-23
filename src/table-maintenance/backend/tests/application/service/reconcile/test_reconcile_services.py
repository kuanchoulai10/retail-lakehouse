"""Test the reconcile planning, submission and job services."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.model.maintenance_run.trigger_type import TriggerType
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.maintenance_settings.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.reconcile.delete_maintenance_job import (
    DeleteMaintenanceJobUseCaseInput,
)
from application.port.inbound.reconcile.get_maintenance_job_status import (
    GetMaintenanceJobStatusUseCaseInput,
)
from application.port.inbound.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceUseCaseInput,
)
from application.port.inbound.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseInputFilterItem,
)
from application.port.outbound.catalog.read_catalog import (
    ReadCatalogGatewayObservation,
)
from application.service.reconcile.delete_maintenance_job import (
    DeleteMaintenanceJobService,
)
from application.service.reconcile.get_maintenance_job_status import (
    GetMaintenanceJobStatusService,
)
from application.service.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceService,
)
from application.service.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationService,
)
from tests.fakes.track_calls import track_calls

NAME = TableName("iceberg", "sales", "orders")
KEY = ("iceberg", "sales", "orders")
OPS = MaintenanceOperation


def _table(repo, now, settings=None, uuid="u-1", name=NAME):
    table = ManagedTable.register_auto(
        TableUuid(uuid),
        name,
        DiscoveryRuleId("r-1"),
        PolicyTemplateId("t-1"),
        settings or MaintenanceSettings(),
        now,
    )
    repo.create(table)
    return table


def _partition(spec_id, values, files=10, size=10 * 1024):
    return {
        "spec_id": spec_id,
        "values": values,
        "data_file_count": files,
        "position_delete_file_count": 0,
        "equality_delete_file_count": 0,
        "total_data_file_size_bytes": size,
    }


def _field(name):
    return {
        "field_id": 1000,
        "name": name,
        "source_column": name,
        "source_type": "string",
        "transform": "identity",
    }


def _observe(catalog, now, **overrides):
    fields: dict[str, Any] = {
        "table_uuid": "u-1",
        "current_snapshot_id": 12,
        "specs": [
            {"spec_id": 0, "fields": [_field("region")]},
            {"spec_id": 1, "fields": [_field("country")]},
        ],
        "partitions": [_partition(0, ["eu"]), _partition(1, ["de"])],
        "manifests": [{"length_bytes": 100}] * 5,
        "snapshots": [
            {
                "snapshot_id": i,
                "committed_at": (now - timedelta(days=10, minutes=i)).isoformat(),
            }
            for i in range(1, 13)
        ],
    }
    fields.update(overrides)
    catalog.add_table(*KEY, "u-1")
    catalog.observations[KEY] = ReadCatalogGatewayObservation(**fields)


@pytest.fixture
def planner(tables_repo, catalog):
    return PlanTableMaintenanceService(tables_repo, catalog)


def _plan(planner, now, manual=None, uuid="u-1"):
    return planner.execute(
        PlanTableMaintenanceUseCaseInput(
            table_uuid=uuid, now=now, manual_operations=manual
        )
    )


# --- plan ---


def test_plan_skip_reasons(planner, tables_repo, catalog, now):
    assert _plan(planner, now, uuid="missing").reason == "dropped"
    dropped = _table(tables_repo, now, uuid="u-d", name=TableName("c", "n", "d"))
    dropped.mark_dropped(now)
    excluded = ManagedTable.exclude_manual(
        TableUuid("u-e"), TableName("c", "n", "e"), now
    )
    tables_repo.create(excluded)
    paused = _table(tables_repo, now, uuid="u-p", name=TableName("c", "n", "p"))
    paused.pause(now)
    gone = _table(tables_repo, now)
    results = {
        uuid: _plan(planner, now, uuid=uuid)
        for uuid in ("u-d", "u-e", "u-p", gone.id.value)
    }
    assert {k: (v.status, v.reason) for k, v in results.items()} == {
        "u-d": ("skip", "dropped"),
        "u-e": ("skip", "excluded"),
        "u-p": ("skip", "paused"),
        "u-1": ("skip", "not_found"),
    }
    assert all(v.operations == [] for v in results.values())
    assert results["u-1"].reconcile_interval_seconds == 3600


def test_plan_compaction_has_one_filter_per_spec(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.status, plan.reason) == ("planned", None)
    compaction = plan.operations[0]
    assert compaction.operation == "rewrite_data_files"
    assert [f.spec_id for f in compaction.filters] == [0, 1]
    assert "'eu'" in compaction.filters[0].where
    assert "'de'" in compaction.filters[1].where
    assert compaction.procedure_args == {
        "target-file-size-bytes": 536870912,
        "min-input-files": 2,
        "partial-progress.enabled": True,
    }


def test_plan_orders_operations_and_renders_procedure_args(
    planner, tables_repo, catalog, now
):
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert [o.operation for o in plan.operations] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]
    by_op = {o.operation: o for o in plan.operations}
    assert by_op["rewrite_manifests"].procedure_args == {}
    assert by_op["rewrite_manifests"].filters == []
    assert by_op["expire_snapshots"].procedure_args == {
        "older_than": "2026-10-23T12:00:00+00:00",
        "retain_last": 10,
    }
    assert by_op["remove_orphan_files"].procedure_args == {
        "older_than": "2026-10-21T12:00:00+00:00"
    }
    assert plan.reconcile_interval_seconds == 3600


def test_plan_target_file_size_comes_from_settings(planner, tables_repo, catalog, now):
    _table(
        tables_repo,
        now,
        MaintenanceSettings(
            reconcile_interval=timedelta(minutes=5),
            rewrite_data_files=RewriteDataFilesSettings(
                target_file_size_bytes=1024, min_reducible_files=1
            ),
        ),
    )
    _observe(
        catalog,
        now,
        specs=[{"spec_id": 0, "fields": []}],
        partitions=[_partition(0, [], files=20, size=2000)],
    )
    plan = _plan(planner, now)
    assert plan.operations[0].procedure_args["target-file-size-bytes"] == 1024
    assert plan.reconcile_interval_seconds == 300


def test_plan_whole_table_compaction_has_no_filters(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(
        catalog,
        now,
        specs=[{"spec_id": 0, "fields": []}],
        partitions=[_partition(0, [], files=20)],
    )
    compaction = _plan(planner, now).operations[0]
    assert compaction.operation == "rewrite_data_files"
    assert compaction.filters == []


def test_scheduled_plan_respects_cooldown(planner, tables_repo, catalog, now):
    table = _table(tables_repo, now)
    for op in OPS.ordered():
        table.record_operation_result(op, True, now - timedelta(minutes=1))
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.status, plan.operations) == ("planned", [])
    table.operation_states.clear()
    control = _plan(planner, now)
    assert "rewrite_data_files" in [o.operation for o in control.operations]


def test_manual_plan_ignores_disabled_and_cooldown(planner, tables_repo, catalog, now):
    settings = MaintenanceSettings(
        rewrite_data_files=RewriteDataFilesSettings(enabled=False)
    )
    table = _table(tables_repo, now, settings)
    table.record_operation_result(OPS.REMOVE_ORPHAN_FILES, True, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["remove_orphan_files", "rewrite_data_files"])
    assert plan.status == "planned"
    assert [o.operation for o in plan.operations] == [
        "rewrite_data_files",
        "remove_orphan_files",
    ]
    assert plan.operations[0].filters == []
    assert plan.operations[1].procedure_args == {
        "older_than": "2026-10-21T12:00:00+00:00"
    }


def test_manual_plan_without_a_catalog_observation_is_skipped_not_found(
    planner, tables_repo, now
):
    _table(tables_repo, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", [])


@pytest.mark.parametrize("manual", [None, ["rewrite_manifests"]])
def test_plan_skips_when_catalog_table_has_a_different_uuid(
    planner, tables_repo, catalog, now, manual
):
    _table(tables_repo, now)
    _observe(catalog, now, table_uuid="u-recreated")
    plan = _plan(planner, now, manual)
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", [])


def test_manual_plan_rejects_unknown_or_empty_operations(planner, tables_repo, now):
    _table(tables_repo, now)
    with pytest.raises(ValidationError):
        _plan(planner, now, ["defragment"])
    with pytest.raises(ValidationError):
        _plan(planner, now, [])


def test_plan_reports_malformed_observation_as_validation_error(
    planner, tables_repo, catalog, now
):
    _table(tables_repo, now)
    _observe(catalog, now, manifests=[{}])
    with pytest.raises(ValidationError):
        _plan(planner, now)


# --- submit ---


@pytest.fixture
def run(runs_repo, tables_repo, now):
    _table(tables_repo, now)
    created = MaintenanceRun.create(
        MaintenanceRunId("run-1"),
        TableUuid("u-1"),
        TriggerType.SCHEDULED,
        [OPS.REWRITE_DATA_FILES, OPS.EXPIRE_SNAPSHOTS],
        now,
    )
    runs_repo.create(created)
    return created


@pytest.fixture
def submitter(runs_repo, tables_repo, submit_job):
    return SubmitMaintenanceOperationService(runs_repo, tables_repo, submit_job)


def _filter(spec_id, where):
    return SubmitMaintenanceOperationUseCaseInputFilterItem(spec_id, where)


def _submit(submitter, now, **overrides):
    fields = {
        "run_id": "run-1",
        "operation": "rewrite_data_files",
        "attempt": 1,
        "filters": [
            SubmitMaintenanceOperationUseCaseInputFilterItem(0, "a = 1"),
            SubmitMaintenanceOperationUseCaseInputFilterItem(1, "b = 2"),
        ],
        "procedure_args": {"min-input-files": 2},
        "callback_base_url": "http://tm.example:8000/",
        "now": now,
    }
    fields.update(overrides)
    return submitter.execute(SubmitMaintenanceOperationUseCaseInput(**fields))


def test_submit_starts_attempt_and_submits_job(submitter, run, submit_job, now):
    out = _submit(submitter, now)
    assert out.app_name == "tm-rdf-run1-a1"
    job = submit_job.jobs[out.app_name]
    assert (job.run_id, job.operation, job.attempt) == (
        "run-1",
        "rewrite_data_files",
        1,
    )
    assert (job.catalog, job.namespace, job.table) == ("iceberg", "sales", "orders")
    assert job.where == ["a = 1", "b = 2"]
    assert job.procedure_args == {"min-input-files": 2}
    assert job.callback_url == (
        "http://tm.example:8000/v1/runs/run-1/operations/rewrite_data_files/result"
    )
    op = run.operations[0]
    assert (op.attempts, op.spark_application) == (1, out.app_name)


def test_submit_saves_run_before_submitting_job(
    submitter, run, runs_repo, submit_job, log, now
):
    track_calls(runs_repo, "update", "runs.update", log, lambda r: r.id.value)
    track_calls(submit_job, "submit", "job.submit", log, lambda i: i.app_name)
    _submit(submitter, now)
    assert log == [("runs.update", "run-1"), ("job.submit", "tm-rdf-run1-a1")]


def test_submit_whole_table_filter_means_no_where(submitter, run, submit_job, now):
    _submit(submitter, now, filters=[_filter(0, "")])
    assert next(iter(submit_job.jobs.values())).where == []


def test_submit_any_empty_where_makes_the_whole_table_the_target(
    submitter, run, submit_job, now
):
    _submit(submitter, now, filters=[_filter(0, "a = 1"), _filter(1, "")])
    assert next(iter(submit_job.jobs.values())).where == []


def test_submit_is_idempotent_by_app_name(submitter, run, submit_job, now):
    first = _submit(submitter, now)
    second = _submit(submitter, now)
    assert first == second
    assert len(submit_job.calls) == 2
    assert len(submit_job.jobs) == 1
    assert run.operations[0].attempts == 1


def test_submit_next_attempt_uses_a_new_application_name(
    submitter, run, submit_job, now
):
    _submit(submitter, now)
    run.fail(OPS.REWRITE_DATA_FILES, 1, "boom", now)
    out = _submit(submitter, now, attempt=2)
    assert out.app_name == "tm-rdf-run1-a2"
    assert len(submit_job.jobs) == 2


def test_submit_rejects_bad_requests(submitter, run, submit_job, tables_repo, now):
    with pytest.raises(NotFoundError):
        _submit(submitter, now, run_id="nope")
    with pytest.raises(ValidationError):
        _submit(submitter, now, operation="defragment")
    with pytest.raises(ConflictError):
        _submit(submitter, now, attempt=3)
    with pytest.raises(ConflictError):
        _submit(submitter, now, operation="remove_orphan_files")
    assert submit_job.calls == []
    del tables_repo.items["u-1"]
    with pytest.raises(NotFoundError):
        _submit(submitter, now)


# --- job status / delete ---


def test_get_job_status_passes_state_and_error_through(read_job):
    read_job.set_state("app-1", "FAILED", "OOM")
    service = GetMaintenanceJobStatusService(read_job)
    out = service.execute(GetMaintenanceJobStatusUseCaseInput("app-1"))
    assert (out.state, out.error) == ("FAILED", "OOM")
    missing = service.execute(GetMaintenanceJobStatusUseCaseInput("app-2"))
    assert (missing.state, missing.error) == ("NOT_FOUND", None)


def test_get_job_status_rejects_unknown_state(read_job):
    read_job.set_state("app-1", "WEIRD")
    with pytest.raises(ValidationError):
        GetMaintenanceJobStatusService(read_job).execute(
            GetMaintenanceJobStatusUseCaseInput("app-1")
        )


def test_delete_job_forwards_to_the_gateway(delete_job):
    out = DeleteMaintenanceJobService(delete_job).execute(
        DeleteMaintenanceJobUseCaseInput("app-1")
    )
    assert out.app_name == "app-1"
    assert [c.app_name for c in delete_job.calls] == ["app-1"]
