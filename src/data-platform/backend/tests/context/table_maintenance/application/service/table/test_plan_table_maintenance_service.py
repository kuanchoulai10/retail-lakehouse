"""Test the reconcile planning, submission and job services."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
    RewriteDataFilesSettings,
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
from context.table_maintenance.application.port.outbound.table import (
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import (
    PlanTableMaintenanceService,
)

NAME = TableName("iceberg", "sales", "orders")
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
    return PlanTableMaintenanceService(tables_repo, catalog)


def _plan(planner, now, manual=None, uuid="u-1"):
    return planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid=uuid, now=now, manual_operations=manual))


# --- plan ---


def test_plan_skip_reasons(planner, tables_repo, catalog, now):
    assert _plan(planner, now, uuid="missing").reason == "dropped"
    dropped = _table(tables_repo, now, uuid="u-d", name=TableName("c", "n", "d"))
    dropped.mark_dropped(now)
    excluded = Table.exclude_manual(TableId("u-e"), TableName("c", "n", "e"), now)
    tables_repo.create(excluded)
    paused = _table(tables_repo, now, uuid="u-p", name=TableName("c", "n", "p"))
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
    _table(tables_repo, now)
    _observe(catalog, now)
    assert _plan(planner, now).table_name == "iceberg.sales.orders"


def test_plan_skip_carries_the_table_name_when_the_table_is_known(planner, tables_repo, catalog, now):
    paused = _table(tables_repo, now, uuid="u-p", name=TableName("c", "n", "p"))
    paused.pause(now)
    assert _plan(planner, now, uuid="u-p").table_name == "c.n.p"
    assert _plan(planner, now, uuid="missing").table_name is None


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


def test_plan_orders_operations_and_renders_procedure_args(planner, tables_repo, catalog, now):
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
    _table(tables_repo, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", [])


@pytest.mark.parametrize("manual", [None, ["rewrite_manifests"]])
def test_plan_skips_when_catalog_table_has_a_different_uuid(planner, tables_repo, catalog, now, manual):
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


def test_plan_reports_malformed_observation_as_validation_error(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now, manifests=[{}])
    with pytest.raises(ValidationError):
        _plan(planner, now)
