"""Test the GetTableHealthService."""

from __future__ import annotations

from typing import Any

import pytest
from context.table_maintenance.application.domain.model.shared import (
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
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableHealthUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import GetTableHealthService

KEY = ("iceberg", "sales", "orders")
NAME = TableName(*KEY)


def _register(repo, now, settings):
    table = Table.register_auto(
        TableId("u-1"),
        NAME,
        TableDiscoveryRuleId("r-1"),
        TableMaintenancePresetId("t-1"),
        settings,
        now,
    )
    repo.create(table)
    return table


def _partition(values, pos=0, eq=0):
    return {
        "spec_id": 0,
        "values": values,
        "data_file_count": 10,
        "position_delete_file_count": pos,
        "equality_delete_file_count": eq,
        "total_data_file_size_bytes": 10 * 1024,
    }


def _observe(catalog, **overrides):
    fields: dict[str, Any] = {
        "table_uuid": "u-1",
        "current_snapshot_id": 12,
        "specs": [],
        "partitions": [_partition(["eu"])],
        "manifests": [],
        "snapshots": [],
    }
    fields.update(overrides)
    catalog.add_table(*KEY, "u-1")
    catalog.observations[KEY] = TableMetadataObservation(**fields)


@pytest.fixture
def service(tables_repo, catalog, clock):
    return GetTableHealthService(tables_repo, catalog, clock=clock)


def _health(service):
    return service.execute(GetTableHealthUseCaseInput(uuid="u-1"))


def test_active_table_reports_each_operation_in_order(
    service, tables_repo, catalog, now
):
    _register(tables_repo, now, MaintenanceSettings())
    _observe(catalog)

    output = _health(service)

    assert output.scheduled is True
    assert output.not_scheduled_reason is None
    assert [item.operation for item in output.operations] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]
    compaction = output.operations[0]
    assert compaction.verdict == "due"
    assert compaction.measured is not None
    assert compaction.size_source == "default"


def test_paused_table_is_not_scheduled_but_assessed(service, tables_repo, catalog, now):
    _register(tables_repo, now, MaintenanceSettings()).pause(now)
    _observe(catalog)

    output = _health(service)

    assert output.scheduled is False
    assert output.not_scheduled_reason == "paused"
    assert len(output.operations) == 4


def test_table_without_settings_has_no_lines(service, tables_repo, catalog, now):
    _register(tables_repo, now, MaintenanceSettings()).settings = None
    _observe(catalog)

    output = _health(service)

    assert output.scheduled is False
    assert output.not_scheduled_reason == "no_settings"
    assert output.operations == []


def test_delete_file_counts_are_summed(service, tables_repo, catalog, now):
    _register(tables_repo, now, MaintenanceSettings())
    _observe(
        catalog,
        partitions=[_partition(["eu"], pos=2, eq=1), _partition(["us"], pos=3, eq=4)],
    )

    output = _health(service)

    assert output.position_delete_files == 5
    assert output.equality_delete_files == 5


def test_health_404_when_not_in_catalog(service, tables_repo, now):
    _register(tables_repo, now, MaintenanceSettings())

    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        _health(service)
