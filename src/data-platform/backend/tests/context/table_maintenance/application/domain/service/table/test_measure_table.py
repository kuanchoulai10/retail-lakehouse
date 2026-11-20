"""Test measuring a table's metrics from its observation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    ManifestStats,
    PartitionStats,
    SnapshotInfo,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS, TableId
from context.table_maintenance.application.domain.service.table import measure_table

NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)


def stats(
    *, data: int, pos: int, eq: int, dv: int, size: int, data_rec: int, pos_rec: int, eq_rec: int
) -> PartitionStats:
    """Build one partition's statistics."""
    return PartitionStats(
        spec_id=0,
        values=(),
        data_file_count=data,
        position_delete_file_count=pos,
        equality_delete_file_count=eq,
        total_data_file_size_bytes=size,
        data_record_count=data_rec,
        position_delete_record_count=pos_rec,
        equality_delete_record_count=eq_rec,
        deletion_vector_count=dv,
    )


def manifest(length: int, *, added: int, existing: int, deleted: int) -> ManifestStats:
    """Build one manifest's statistics."""
    return ManifestStats(length_bytes=length, added_entries=added, existing_entries=existing, deleted_entries=deleted)


def observation_with(
    *,
    partitions: tuple[PartitionStats, ...] = (),
    manifests: tuple[ManifestStats, ...] = (),
    snapshot_count: int = 0,
    properties: dict[str, str] | None = None,
) -> TableObservation:
    """Build an observation of a table with the given layout."""
    snapshots = tuple(SnapshotInfo(snapshot_id=i, committed_at=NOW) for i in range(snapshot_count))
    return TableObservation(
        table_uuid="t1",
        properties=properties or {},
        current_snapshot_id=None if snapshot_count == 0 else snapshot_count - 1,
        specs=(),
        partitions=partitions,
        manifests=manifests,
        snapshots=snapshots,
    )


def test_measure_sums_every_partition():
    """Each count is the sum over partitions or manifests; deletion vectors leave the position-delete files."""
    observation = observation_with(
        partitions=(
            stats(data=3, pos=2, eq=1, dv=1, size=300, data_rec=30, pos_rec=8, eq_rec=4),
            stats(data=2, pos=0, eq=0, dv=0, size=200, data_rec=20, pos_rec=0, eq_rec=0),
        ),
        manifests=(manifest(100, added=3, existing=1, deleted=0), manifest(50, added=2, existing=0, deleted=1)),
        snapshot_count=4,
    )
    m = measure_table(TableId("t1"), observation, NOW)
    assert m.table_id == TableId("t1")
    assert (m.data_files, m.position_delete_files, m.equality_delete_files, m.deletion_vectors) == (5, 1, 1, 1)
    assert (m.data_size_bytes, m.data_records, m.position_delete_records, m.equality_delete_records) == (500, 50, 8, 4)
    assert (m.manifests, m.manifests_size_bytes) == (2, 150)
    assert (m.manifest_added_entries, m.manifest_existing_entries, m.manifest_deleted_entries) == (5, 1, 1)
    assert m.snapshots == 4
    assert m.observed_at == NOW


def test_reducible_files_use_the_tables_target_size():
    """Four files holding 250 bytes need three files at a 100-byte target, so one could go."""
    observation = observation_with(
        partitions=(stats(data=4, pos=0, eq=0, dv=0, size=250, data_rec=0, pos_rec=0, eq_rec=0),),
        properties={"write.target-file-size-bytes": "100"},
    )
    assert measure_table(TableId("t1"), observation, NOW).reducible_files == 1


def test_reducible_files_are_summed_per_partition():
    """Each partition of three 40-byte files needs two 100-byte files, so one goes from each: two in all.

    The table's totals (six files, 240 bytes) would give three, but compaction never merges across partitions.
    """
    observation = observation_with(
        partitions=(
            stats(data=3, pos=0, eq=0, dv=0, size=120, data_rec=0, pos_rec=0, eq_rec=0),
            stats(data=3, pos=0, eq=0, dv=0, size=120, data_rec=0, pos_rec=0, eq_rec=0),
        ),
        properties={"write.target-file-size-bytes": "100"},
    )
    assert measure_table(TableId("t1"), observation, NOW).reducible_files == 2


def test_more_deletion_vectors_than_position_delete_files_is_refused():
    """Deletion vectors are counted among the position-delete files, so more of them is an invariant violation."""
    observation = observation_with(
        partitions=(stats(data=1, pos=1, eq=0, dv=2, size=10, data_rec=1, pos_rec=2, eq_rec=0),),
    )
    with pytest.raises(InvariantViolation):
        measure_table(TableId("t1"), observation, NOW)


def test_reducible_files_default_to_the_platform_target_when_the_table_sets_none():
    """Without the property the 512 MiB default applies, so four small files reduce to one."""
    observation = observation_with(
        partitions=(stats(data=4, pos=0, eq=0, dv=0, size=250, data_rec=0, pos_rec=0, eq_rec=0),),
    )
    assert measure_table(TableId("t1"), observation, NOW).reducible_files == 3


def test_table_without_snapshot_measures_zero():
    """A table never written to has every count at zero, not a skip."""
    m = measure_table(TableId("t1"), observation_with(), NOW)
    assert all(getattr(m, field) == 0 for field in TABLE_METRIC_COUNT_FIELDS)
