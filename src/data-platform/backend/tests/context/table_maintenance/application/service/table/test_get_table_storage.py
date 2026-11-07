"""Test the GetTableStorageService."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
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
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableStorageUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    TableStorageMeasure,
)
from context.table_maintenance.application.service.table import GetTableStorageService

KEY = ("iceberg", "sales", "orders")
OPS = MaintenanceOperation


def _register(repo, now):
    repo.create(
        Table.register_auto(
            TableId("u-1"),
            TableName(*KEY),
            TableDiscoveryRuleId("r-1"),
            TableMaintenancePresetId("t-1"),
            MaintenanceSettings(),
            now,
        )
    )


def _measure(catalog, **overrides):
    fields = {
        "table_uuid": "u-1",
        "current_bytes": 1000,
        "current_files": 10,
        "referenced_bytes": 4000,
        "referenced_files": 25,
    }
    fields.update(overrides)
    catalog.add_table(*KEY, "u-1")
    catalog.storage_measures[KEY] = TableStorageMeasure(**fields)


def _run(runs_repo, run_id, at, results):
    """results maps operation to (succeeded, metrics)."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(run_id),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        list(results),
        at,
        execution_ref=f"wf-{run_id}",
    )
    for op, (ok, metrics) in results.items():
        run.start_attempt(op, 1, None, at)
        if ok:
            run.succeed(op, 1, metrics, at)
        else:
            run.fail(op, 1, "boom", at)
    runs_repo.create(run)


@pytest.fixture
def service(tables_repo, catalog, runs_repo, clock):
    return GetTableStorageService(tables_repo, catalog, runs_repo, clock=clock)


def _storage(service):
    return service.execute(GetTableStorageUseCaseInput(uuid="u-1"))


def test_storage_splits_current_and_old_snapshot_bytes(service, tables_repo, catalog, now):
    _register(tables_repo, now)
    _measure(catalog)

    output = _storage(service)

    assert output.current_bytes == 1000
    assert output.current_files == 10
    assert output.old_snapshot_bytes == 3000
    assert output.old_snapshot_files == 15
    assert output.window_days == 30
    assert output.reclaimed == {
        "rewritten_data_files": 0,
        "added_data_files": 0,
        "rewritten_bytes": 0,
        "rewritten_manifests": 0,
        "added_manifests": 0,
        "expired_snapshots": 0,
        "deleted_data_files": 0,
        "deleted_manifest_files": 0,
        "deleted_position_delete_files": 0,
        "deleted_equality_delete_files": 0,
    }
    assert output.attempts_without_metrics == 0


def test_old_snapshot_figures_floor_at_zero(service, tables_repo, catalog, now):
    _register(tables_repo, now)
    _measure(catalog, referenced_bytes=500, referenced_files=4)

    output = _storage(service)

    assert output.old_snapshot_bytes == 0
    assert output.old_snapshot_files == 0


def test_reclaimed_sums_metric_keys(service, tables_repo, catalog, runs_repo, now):
    _register(tables_repo, now)
    _measure(catalog)
    _run(
        runs_repo,
        "r1",
        now - timedelta(days=1),
        {
            OPS.REWRITE_DATA_FILES: (
                True,
                {
                    "rewritten_data_files_count": 20,
                    "added_data_files_count": 5,
                    "rewritten_bytes_count": 17737,
                },
            ),
            OPS.EXPIRE_SNAPSHOTS: (True, {"deleted_manifest_lists_count": 22}),
        },
    )
    _run(
        runs_repo,
        "r2",
        now - timedelta(days=2),
        {
            OPS.REWRITE_DATA_FILES: (True, {"rewritten_data_files_count": 3}),
            OPS.REWRITE_MANIFESTS: (
                True,
                {"rewritten_manifests_count": 4, "added_manifests_count": 1},
            ),
            OPS.EXPIRE_SNAPSHOTS: (
                True,
                {
                    "deleted_manifest_lists_count": 1,
                    "deleted_data_files_count": 7,
                    "deleted_manifest_files_count": 2,
                    "deleted_position_delete_files_count": 3,
                    "deleted_equality_delete_files_count": 4,
                },
            ),
        },
    )
    _run(
        runs_repo,
        "too-old",
        now - timedelta(days=31),
        {OPS.REWRITE_DATA_FILES: (True, {"rewritten_data_files_count": 999})},
    )

    reclaimed = _storage(service).reclaimed

    assert reclaimed["rewritten_data_files"] == 23
    assert reclaimed["added_data_files"] == 5
    assert reclaimed["rewritten_bytes"] == 17737
    assert reclaimed["rewritten_manifests"] == 4
    assert reclaimed["added_manifests"] == 1
    assert reclaimed["expired_snapshots"] == 23
    assert reclaimed["deleted_data_files"] == 7
    assert reclaimed["deleted_manifest_files"] == 2
    assert reclaimed["deleted_position_delete_files"] == 3
    assert reclaimed["deleted_equality_delete_files"] == 4


def test_failed_operations_add_nothing(service, tables_repo, catalog, runs_repo, now):
    _register(tables_repo, now)
    _measure(catalog)
    _run(
        runs_repo,
        "r1",
        now - timedelta(days=1),
        {
            OPS.REWRITE_DATA_FILES: (False, {}),
            OPS.EXPIRE_SNAPSHOTS: (True, {"deleted_manifest_lists_count": 2}),
        },
    )

    output = _storage(service)

    assert output.reclaimed["rewritten_data_files"] == 0
    assert output.reclaimed["expired_snapshots"] == 2
    assert output.attempts_without_metrics == 0


def test_counts_attempts_without_metrics(service, tables_repo, catalog, runs_repo, now):
    _register(tables_repo, now)
    _measure(catalog)
    _run(
        runs_repo,
        "r1",
        now - timedelta(days=1),
        {
            OPS.REWRITE_DATA_FILES: (True, {"completed_without_callback": 1}),
            OPS.REWRITE_MANIFESTS: (True, {"completed_without_callback": 1}),
            OPS.EXPIRE_SNAPSHOTS: (True, {"deleted_manifest_lists_count": 2}),
        },
    )

    output = _storage(service)

    assert output.attempts_without_metrics == 2
    assert output.reclaimed["expired_snapshots"] == 2
    assert output.reclaimed["rewritten_data_files"] == 0


def test_unknown_table_raises_not_found(service):
    with pytest.raises(NotFoundError):
        _storage(service)


def test_table_missing_in_catalog_raises_not_found(service, tables_repo, now):
    _register(tables_repo, now)

    with pytest.raises(NotFoundError, match="is not in the catalog"):
        _storage(service)


def test_storage_404_when_catalog_table_has_another_uuid(service, tables_repo, catalog, now):
    _register(tables_repo, now)
    _measure(catalog, table_uuid="u-recreated")

    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        _storage(service)
