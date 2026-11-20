"""Test the table_observation_from_gateway conversion."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ManifestStats,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SnapshotInfo,
)
from context.table_maintenance.application.port.outbound.table import (
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import (
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
    return TableMetadataObservation(**fields)


def test_converts_every_part_of_the_observation():
    """Every part of the gateway observation is converted to the domain observation."""
    result = table_observation_from_gateway(_gateway_observation())
    assert result.table_uuid == "u-1"
    assert result.properties == {"write.target-file-size-bytes": "1024"}
    assert result.current_snapshot_id == 7
    assert result.specs == (
        PartitionSpecInfo(
            spec_id=0,
            fields=(
                PartitionFieldInfo(
                    field_id=1000, name="region", source_column="region", source_type="string", transform="identity"
                ),
            ),
        ),
    )
    assert result.partitions == (
        PartitionStats(
            spec_id=0,
            values=("eu",),
            data_file_count=4,
            position_delete_file_count=1,
            equality_delete_file_count=2,
            total_data_file_size_bytes=4096,
        ),
    )
    assert result.manifests == (ManifestStats(length_bytes=100), ManifestStats(length_bytes=200))
    assert [s.snapshot_id for s in result.snapshots] == [6, 7, 8]


def test_committed_at_becomes_aware_utc():
    """Snapshot commit times become timezone aware in UTC."""
    result = table_observation_from_gateway(_gateway_observation())
    assert result.snapshots[0] == SnapshotInfo(snapshot_id=6, committed_at=datetime(2026, 10, 1, 8, 0, tzinfo=UTC))
    assert result.snapshots[1].committed_at == datetime(2026, 10, 2, 10, tzinfo=UTC)
    assert result.snapshots[2].committed_at == datetime(2026, 10, 3, 10, tzinfo=UTC)
    assert all(s.committed_at.utcoffset() == timedelta(0) for s in result.snapshots)


def test_empty_observation_converts_to_empty_tuples():
    """An empty observation converts to empty tuples."""
    result = table_observation_from_gateway(TableMetadataObservation(table_uuid="u-2"))
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
    """A malformed item in the observation raises ValueError."""
    with pytest.raises(ValueError):
        table_observation_from_gateway(_gateway_observation(**overrides))


def test_partition_last_written_at_becomes_aware_utc():
    """A partition's last write time becomes timezone aware in UTC; an unknown one stays None."""
    partition = {
        "spec_id": 0,
        "values": ["eu"],
        "data_file_count": 1,
        "position_delete_file_count": 0,
        "equality_delete_file_count": 0,
        "total_data_file_size_bytes": 10,
    }
    result = table_observation_from_gateway(
        _gateway_observation(
            partitions=[
                {**partition, "last_written_at": "2026-10-01T10:00:00+02:00"},
                {**partition, "values": ["us"], "last_written_at": None},
                {**partition, "values": ["ap"]},
            ]
        )
    )
    assert [p.last_written_at for p in result.partitions] == [datetime(2026, 10, 1, 8, tzinfo=UTC), None, None]


def test_converter_defaults_missing_counts_to_zero():
    """Partition and manifest items without the record, deletion vector and entry counts convert with zeros."""
    result = table_observation_from_gateway(_gateway_observation())
    partition = result.partitions[0]
    assert (
        partition.data_record_count,
        partition.position_delete_record_count,
        partition.equality_delete_record_count,
        partition.deletion_vector_count,
    ) == (0, 0, 0, 0)
    assert all((m.added_entries, m.existing_entries, m.deleted_entries) == (0, 0, 0) for m in result.manifests)


def test_converter_carries_the_record_deletion_vector_and_entry_counts():
    """The new counts of a partition and a manifest item reach the domain observation."""
    result = table_observation_from_gateway(
        _gateway_observation(
            partitions=[
                {
                    "spec_id": 0,
                    "values": ["eu"],
                    "data_file_count": 1,
                    "position_delete_file_count": 2,
                    "equality_delete_file_count": 1,
                    "total_data_file_size_bytes": 10,
                    "data_record_count": 30,
                    "position_delete_record_count": 10,
                    "equality_delete_record_count": 7,
                    "deletion_vector_count": 1,
                }
            ],
            manifests=[{"length_bytes": 100, "added_entries": 3, "existing_entries": 2, "deleted_entries": 1}],
        )
    )
    assert (
        result.partitions[0].data_record_count,
        result.partitions[0].position_delete_record_count,
        result.partitions[0].equality_delete_record_count,
        result.partitions[0].deletion_vector_count,
    ) == (30, 10, 7, 1)
    assert result.manifests == (
        ManifestStats(length_bytes=100, added_entries=3, existing_entries=2, deleted_entries=1),
    )
