"""Test the GetTableMetadataService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from application.domain.model.shared import MaintenanceSettings
from application.domain.model.table import Table, TableId, TableName
from application.domain.model.table_discovery_rule import TableDiscoveryRuleId
from application.domain.model.table_maintenance_preset import TableMaintenancePresetId
from application.exceptions import NotFoundError
from application.port.inbound.table import GetTableMetadataUseCaseInput
from application.port.outbound.table import TableDescription
from application.service.table import GetTableMetadataService

KEY = ("iceberg", "sales", "orders")


@pytest.fixture
def service(tables_repo, catalog, now):
    tables_repo.create(
        Table.register_auto(
            TableId("u-1"),
            TableName(*KEY),
            TableDiscoveryRuleId("r-1"),
            TableMaintenancePresetId("t-1"),
            MaintenanceSettings(),
            now,
        )
    )
    return GetTableMetadataService(tables_repo, catalog)


def _describe(catalog, **overrides: Any):
    fields: dict[str, Any] = {
        "table_uuid": "u-1",
        "format_version": 2,
        "location": "s3://w/orders",
    }
    fields.update(overrides)
    catalog.descriptions[KEY] = TableDescription(**fields)


def test_metadata_maps_summary_totals(service, catalog):
    _describe(
        catalog,
        current_snapshot_id=7,
        snapshot_count=3,
        last_committed_at="2026-10-24T12:00:00+00:00",
        properties={"write.format.default": "parquet"},
        current_summary={
            "total-records": "1204331",
            "total-data-files": "15",
            "total-files-size": "50540544",
        },
    )

    output = service.execute(GetTableMetadataUseCaseInput(uuid="u-1"))

    assert output.total_records == 1204331
    assert output.total_data_files == 15
    assert output.total_delete_files is None
    assert output.total_files_size_bytes == 50540544
    assert output.current_snapshot_id == 7
    assert output.snapshot_count == 3
    assert output.last_committed_at == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert output.properties == {"write.format.default": "parquet"}
    assert output.format_version == 2
    assert output.location == "s3://w/orders"


def test_metadata_ignores_non_numeric_totals(service, catalog):
    _describe(catalog, current_summary={"total-records": "n/a"})

    output = service.execute(GetTableMetadataUseCaseInput(uuid="u-1"))

    assert output.total_records is None


def test_metadata_of_empty_table(service, catalog):
    _describe(catalog)

    output = service.execute(GetTableMetadataUseCaseInput(uuid="u-1"))

    assert output.snapshot_count == 0
    assert output.last_committed_at is None
    assert output.total_records is None
    assert output.total_data_files is None
    assert output.total_delete_files is None
    assert output.total_files_size_bytes is None


def test_metadata_unknown_table_raises_not_found(service):
    with pytest.raises(NotFoundError, match="table u-9 not found"):
        service.execute(GetTableMetadataUseCaseInput(uuid="u-9"))


def test_metadata_404_when_not_in_catalog(service):
    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        service.execute(GetTableMetadataUseCaseInput(uuid="u-1"))


def test_metadata_404_when_catalog_table_has_another_uuid(service, catalog):
    _describe(catalog, table_uuid="u-recreated")

    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        service.execute(GetTableMetadataUseCaseInput(uuid="u-1"))
