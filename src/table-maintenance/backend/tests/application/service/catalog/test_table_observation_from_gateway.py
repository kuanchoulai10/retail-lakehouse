"""Test the table_observation_from_gateway conversion."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from application.domain.model.observation.manifest_stats import ManifestStats
from application.domain.model.observation.partition_field_info import (
    PartitionFieldInfo,
)
from application.domain.model.observation.partition_spec_info import (
    PartitionSpecInfo,
)
from application.domain.model.observation.partition_stats import PartitionStats
from application.domain.model.observation.snapshot_info import SnapshotInfo
from application.port.outbound.catalog.read_catalog import (
    ReadCatalogGatewayObservation,
)
from application.service.catalog.table_observation_from_gateway import (
    table_observation_from_gateway,
)


def _gateway_observation(**overrides):
    fields = {
        "table_uuid": "u-1",
        "properties": {"write.target-file-size-bytes": "1024"},
        "current_snapshot_id": 7,
        "specs": [
            {
                "spec_id": 0,
                "fields": [
                    {
                        "field_id": 1000,
                        "name": "region",
                        "source_column": "region",
                        "source_type": "string",
                        "transform": "identity",
                    }
                ],
            }
        ],
        "partitions": [
            {
                "spec_id": 0,
                "values": ["eu"],
                "data_file_count": 4,
                "position_delete_file_count": 1,
                "equality_delete_file_count": 2,
                "total_data_file_size_bytes": 4096,
            }
        ],
        "manifests": [{"length_bytes": 100}, {"length_bytes": 200}],
        "snapshots": [
            {"snapshot_id": 6, "committed_at": "2026-10-01T10:00:00+02:00"},
            {"snapshot_id": 7, "committed_at": "2026-10-02T10:00:00"},
            {"snapshot_id": 8, "committed_at": "2026-10-03T10:00:00Z"},
        ],
    }
    fields.update(overrides)
    return ReadCatalogGatewayObservation(**fields)


def test_converts_every_part_of_the_observation():
    result = table_observation_from_gateway(_gateway_observation())
    assert result.table_uuid == "u-1"
    assert result.properties == {"write.target-file-size-bytes": "1024"}
    assert result.current_snapshot_id == 7
    assert result.specs == (
        PartitionSpecInfo(
            0, (PartitionFieldInfo(1000, "region", "region", "string", "identity"),)
        ),
    )
    assert result.partitions == (PartitionStats(0, ("eu",), 4, 1, 2, 4096),)
    assert result.manifests == (ManifestStats(100), ManifestStats(200))
    assert [s.snapshot_id for s in result.snapshots] == [6, 7, 8]


def test_committed_at_becomes_aware_utc():
    result = table_observation_from_gateway(_gateway_observation())
    assert result.snapshots[0] == SnapshotInfo(
        6, datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    )
    assert result.snapshots[1].committed_at == datetime(2026, 10, 2, 10, tzinfo=UTC)
    assert result.snapshots[2].committed_at == datetime(2026, 10, 3, 10, tzinfo=UTC)
    assert all(s.committed_at.utcoffset() == timedelta(0) for s in result.snapshots)


def test_empty_observation_converts_to_empty_tuples():
    result = table_observation_from_gateway(
        ReadCatalogGatewayObservation(table_uuid="u-2")
    )
    assert result.specs == result.partitions == result.manifests == ()
    assert result.snapshots == ()
    assert result.current_snapshot_id is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"manifests": [{}]},
        {"snapshots": [{"snapshot_id": 1, "committed_at": "not a time"}]},
    ],
)
def test_malformed_items_raise_value_error(overrides):
    with pytest.raises(ValueError):
        table_observation_from_gateway(_gateway_observation(**overrides))
