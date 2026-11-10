"""Test the reconcile planning, submission and job services."""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
    RewriteDataFilesSettings,
    RewriteManifestsSettings,
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
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import (
    PlanTableMaintenanceService,
)
from context.table_maintenance.application.service.table_reconciliation import (
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

NAME = TableName(catalog="iceberg", namespace="sales", table="orders")
KEY = ("iceberg", "sales", "orders")
OPS = MaintenanceOperation


def _table(repo, now, settings=None, uuid="u-1", name=NAME):
    table = Table.register_auto(
        TableId(uuid),
        name,
        TableDiscoveryRuleId("r-1"),
        TableMaintenancePresetId("t-1"),
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
    catalog.observations[KEY] = TableMetadataObservation(**fields)


@pytest.fixture
def planner(tables_repo, catalog):
    """Provide the plan table maintenance service on the fakes."""
    return PlanTableMaintenanceService(tables_repo, catalog)


def _plan(planner, now, manual=None, uuid="u-1"):
    return planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid=uuid, now=now, manual_operations=manual))


# --- plan ---


def test_plan_skip_reasons(planner, tables_repo, catalog, now):
    """Each table that cannot be planned is skipped with the reason for it."""
    assert _plan(planner, now, uuid="missing").reason == "dropped"
    dropped = _table(tables_repo, now, uuid="u-d", name=TableName(catalog="c", namespace="n", table="d"))
    dropped.mark_dropped(now)
    excluded = Table.exclude_manual(TableId("u-e"), TableName(catalog="c", namespace="n", table="e"), now)
    tables_repo.create(excluded)
    paused = _table(tables_repo, now, uuid="u-p", name=TableName(catalog="c", namespace="n", table="p"))
    paused.pause(now)
    gone = _table(tables_repo, now)
    results = {uuid: _plan(planner, now, uuid=uuid) for uuid in ("u-d", "u-e", "u-p", gone.id.value)}
    assert {k: (v.status, v.reason) for k, v in results.items()} == {
        "u-d": ("skip", "dropped"),
        "u-e": ("skip", "excluded"),
        "u-p": ("skip", "paused"),
        "u-1": ("skip", "not_found"),
    }
    assert all(v.operations == [] for v in results.values())
    assert results["u-1"].reconcile_interval_seconds == 3600


def test_plan_carries_the_fully_qualified_table_name(planner, tables_repo, catalog, now):
    """The plan carries the fully qualified table name."""
    _table(tables_repo, now)
    _observe(catalog, now)
    assert _plan(planner, now).table_name == "iceberg.sales.orders"


def test_plan_skip_carries_the_table_name_when_the_table_is_known(planner, tables_repo, catalog, now):
    """A skipped plan carries the table name when the table is known and None otherwise."""
    paused = _table(tables_repo, now, uuid="u-p", name=TableName(catalog="c", namespace="n", table="p"))
    paused.pause(now)
    assert _plan(planner, now, uuid="u-p").table_name == "c.n.p"
    assert _plan(planner, now, uuid="missing").table_name is None


def test_plan_compaction_has_one_filter_per_spec(planner, tables_repo, catalog, now):
    """A compaction plan has one filter per partition spec."""
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


def test_plan_orders_operations_and_renders_procedure_args(planner, tables_repo, catalog, now):
    """The plan orders its operations and renders the arguments of each procedure."""
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
    assert by_op["remove_orphan_files"].procedure_args == {"older_than": "2026-10-21T12:00:00+00:00"}
    assert plan.reconcile_interval_seconds == 3600


def test_plan_target_file_size_comes_from_settings(planner, tables_repo, catalog, now):
    """The target file size and reconcile interval in the plan come from the settings."""
    _table(
        tables_repo,
        now,
        MaintenanceSettings(
            reconcile_interval=timedelta(minutes=5),
            rewrite_data_files=RewriteDataFilesSettings(target_file_size_bytes=1024, min_reducible_files=1),
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
    """A whole table compaction has no filters."""
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


def test_plan_unsupported_partition_field_falls_back_to_whole_table_compaction(
    planner, tables_repo, catalog, now, caplog
):
    """A partition field that cannot be filtered falls back to whole table compaction and logs it."""
    _table(tables_repo, now)
    binary = {**_field("payload"), "source_type": "binary"}
    _observe(
        catalog,
        now,
        specs=[{"spec_id": 0, "fields": [binary]}],
        partitions=[_partition(0, ["AAE="], files=20)],
    )
    plan = _plan(planner, now)
    assert [o.operation for o in plan.operations] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]
    assert plan.operations[0].filters == []
    assert "whole table" in caplog.text
    assert "binary" in caplog.text


def test_scheduled_plan_respects_cooldown(planner, tables_repo, catalog, now):
    """A scheduled plan respects the cooldown."""
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
    """A manual plan ignores both disabled settings and the cooldown."""
    settings = MaintenanceSettings(rewrite_data_files=RewriteDataFilesSettings(enabled=False))
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
    assert plan.operations[1].procedure_args == {"older_than": "2026-10-21T12:00:00+00:00"}


def test_manual_plan_without_a_catalog_observation_is_skipped_not_found(planner, tables_repo, now):
    """A manual plan for a table missing from the catalog is skipped as not found."""
    _table(tables_repo, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", [])


@pytest.mark.parametrize("manual", [None, ["rewrite_manifests"]])
def test_plan_skips_when_catalog_table_has_a_different_uuid(planner, tables_repo, catalog, now, manual):
    """A plan is skipped as not found when the catalog table has a different uuid."""
    _table(tables_repo, now)
    _observe(catalog, now, table_uuid="u-recreated")
    plan = _plan(planner, now, manual)
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", [])


def test_manual_plan_rejects_unknown_or_empty_operations(planner, tables_repo, now):
    """A manual plan with unknown or no operations is rejected."""
    _table(tables_repo, now)
    with pytest.raises(ValidationError):
        _plan(planner, now, ["defragment"])
    with pytest.raises(ValidationError):
        _plan(planner, now, [])


def test_plan_reports_malformed_observation_as_validation_error(planner, tables_repo, catalog, now):
    """A malformed observation from the catalog is reported as a ValidationError."""
    _table(tables_repo, now)
    _observe(catalog, now, manifests=[{}])
    with pytest.raises(ValidationError):
        _plan(planner, now)


# --- checks and dry run ---


def _checks(plan):
    return {c.operation: c for c in plan.checks}


def test_scheduled_plan_reports_a_check_per_operation(planner, tables_repo, catalog, now):
    """A scheduled plan reports one check per operation with its verdict and measurements."""
    settings = MaintenanceSettings(rewrite_manifests=RewriteManifestsSettings(enabled=False))
    table = _table(tables_repo, now, settings)
    table.record_operation_result(OPS.EXPIRE_SNAPSHOTS, True, now - timedelta(minutes=1))
    _observe(catalog, now)
    plan = _plan(planner, now)
    checks = _checks(plan)
    assert [c.operation for c in plan.checks] == [o.value for o in OPS.ordered()]
    assert checks["rewrite_data_files"].verdict == "due"
    assert checks["rewrite_manifests"].verdict == "off"
    assert checks["expire_snapshots"].verdict == "cooling_down"
    assert checks["expire_snapshots"].next_eligible_at is not None
    assert checks["rewrite_data_files"].next_eligible_at is None
    assert checks["rewrite_data_files"].combine == "all"
    first = checks["rewrite_data_files"].measurements[0]
    assert (first.key, first.unit, first.comparison, first.met) == ("reducible_files", "count", ">=", True)
    assert isinstance(first.observed, int)
    assert [o.operation for o in plan.operations] == [c.operation for c in plan.checks if c.verdict == "due"]
    assert plan.dry_run is False
    assert plan.table_found is True


def test_dry_run_plans_no_operations_but_reports_due(planner, tables_repo, catalog, now):
    """In dry run a scheduled plan has no operations while its checks still say due."""
    _table(tables_repo, now, MaintenanceSettings(dry_run=True))
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.status, plan.operations, plan.dry_run) == ("planned", [], True)
    assert _checks(plan)["rewrite_data_files"].verdict == "due"


def test_manual_plan_runs_in_dry_run(planner, tables_repo, catalog, now):
    """A manual plan still returns its operations when the table is in dry run."""
    _table(tables_repo, now, MaintenanceSettings(dry_run=True))
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    assert [o.operation for o in plan.operations] == ["rewrite_manifests"]
    assert plan.dry_run is True


def test_manual_plan_marks_unrequested_not_checked(planner, tables_repo, catalog, now):
    """A manual plan marks the requested operations due and the rest not checked."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    verdicts = {c.operation: c.verdict for c in plan.checks}
    assert verdicts == {
        "rewrite_data_files": "not_checked",
        "rewrite_manifests": "due",
        "expire_snapshots": "not_checked",
        "remove_orphan_files": "not_checked",
    }
    assert all(c.measurements == [] and c.next_eligible_at is None for c in plan.checks)


def test_missing_table_is_not_found_in_maintenance(planner, now):
    """A table missing from maintenance is skipped as dropped and flagged not found."""
    plan = _plan(planner, now, uuid="missing")
    assert (plan.status, plan.reason, plan.table_found, plan.checks, plan.dry_run) == (
        "skip",
        "dropped",
        False,
        [],
        False,
    )


def test_paused_table_skips_with_table_found(planner, tables_repo, now):
    """A paused table is skipped but the table is found."""
    _table(tables_repo, now).pause(now)
    plan = _plan(planner, now)
    assert (plan.status, plan.reason, plan.table_found, plan.checks) == ("skip", "paused", True, [])


def _record(plan, now, **overrides):
    repo = InMemoryTableReconciliationsRepo()
    fields = {
        "reconciliation_id": "rec-1",
        "table_uuid": "u-1",
        "reconciled_at": now,
        "wake_reasons": {"schedule": 1},
        "dry_run": True,
        "status": plan.status,
        "skip_reason": plan.reason,
        "checks": [asdict(check) for check in plan.checks],
        "run_id": None,
        "run_start_failed": False,
    }
    fields.update(overrides)
    RecordTableReconciliationService(repo).execute(RecordTableReconciliationUseCaseInput(**fields))
    return repo.list_all()[0]


def test_scheduled_plan_checks_can_be_recorded(planner, tables_repo, catalog, now):
    """The checks of a scheduled plan (due, off, cooling down, not needed) are accepted by the record service."""
    settings = MaintenanceSettings(rewrite_manifests=RewriteManifestsSettings(enabled=False))
    table = _table(tables_repo, now, settings)
    table.record_operation_result(OPS.EXPIRE_SNAPSHOTS, True, now - timedelta(minutes=1))
    _observe(catalog, now)
    plan = _plan(planner, now)
    record = _record(plan, now)
    results = {op.operation.value: op.result.value for op in record.operations}
    assert results["rewrite_manifests"] == "off"
    assert results["expire_snapshots"] == "cooling_down"
    assert results["rewrite_data_files"] == "would_start"


def test_manual_plan_checks_can_be_recorded(planner, tables_repo, catalog, now):
    """The checks of a manual plan (due and not checked) are accepted by the record service."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_data_files"])
    record = _record(plan, now)
    results = {op.operation.value: op.result.value for op in record.operations}
    assert results["rewrite_data_files"] == "would_start"
    assert results["expire_snapshots"] == "not_checked"
