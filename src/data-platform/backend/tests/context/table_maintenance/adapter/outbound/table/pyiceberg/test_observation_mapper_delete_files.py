"""Test how the observation mapper counts data and delete files per partition."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from pyiceberg.manifest import (
    DataFile,
    DataFileContent,
    FileFormat,
    ManifestEntry,
    ManifestEntryStatus,
)
from pyiceberg.typedef import Record

from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    observation_from_table,
)

if TYPE_CHECKING:
    from pyiceberg.table import Table


def _entry(  # noqa: ANN202
    content: DataFileContent,
    partition: tuple[Any, ...],
    size: int,
    records: int = 1,
    file_format: FileFormat = FileFormat.PARQUET,
):
    data_file = DataFile.from_args(
        content=content,
        partition=Record(*partition),
        file_size_in_bytes=size,
        record_count=records,
        file_format=file_format,
    )
    data_file.spec_id = 0
    return ManifestEntry.from_args(status=ManifestEntryStatus.ADDED, data_file=data_file)


def _table(entries: list[ManifestEntry]) -> SimpleNamespace:
    manifest = SimpleNamespace(
        manifest_length=10,
        added_files_count=None,
        existing_files_count=None,
        deleted_files_count=None,
        partition_spec_id=0,
        fetch_manifest_entry=lambda io, discard_deleted=True: entries,
    )
    snapshot = SimpleNamespace(snapshot_id=5, manifests=lambda io: [manifest], timestamp_ms=0)
    return SimpleNamespace(
        io=None,
        metadata=SimpleNamespace(
            table_uuid="u",
            properties={},
            partition_specs=[],
            snapshots=[snapshot],
            snapshot_by_id=lambda snapshot_id: None,
        ),
        current_snapshot=lambda: snapshot,
    )


def test_counts_each_content_type_and_sums_only_data_file_sizes() -> None:
    """Each file content type is counted and only data file sizes are summed."""
    table = _table(
        [
            _entry(DataFileContent.DATA, (1,), 100),
            _entry(DataFileContent.DATA, (1,), 50),
            _entry(DataFileContent.POSITION_DELETES, (1,), 7),
            _entry(DataFileContent.EQUALITY_DELETES, (1,), 9),
            _entry(DataFileContent.EQUALITY_DELETES, (1,), 9),
            _entry(DataFileContent.POSITION_DELETES, (2,), 1000),
        ]
    )

    observation = observation_from_table(cast("Table", table))

    assert observation.partitions == [
        {
            "spec_id": 0,
            "values": [1],
            "data_file_count": 2,
            "position_delete_file_count": 1,
            "equality_delete_file_count": 2,
            "total_data_file_size_bytes": 150,
            "data_record_count": 2,
            "position_delete_record_count": 1,
            "equality_delete_record_count": 2,
            "deletion_vector_count": 0,
            "last_written_at": None,
        },
        {
            "spec_id": 0,
            "values": [2],
            "data_file_count": 0,
            "position_delete_file_count": 1,
            "equality_delete_file_count": 0,
            "total_data_file_size_bytes": 0,
            "data_record_count": 0,
            "position_delete_record_count": 1,
            "equality_delete_record_count": 0,
            "deletion_vector_count": 0,
            "last_written_at": None,
        },
    ]


def test_deletion_vectors_are_counted_apart() -> None:
    """A Puffin position delete is a deletion vector, still a position delete file; its records are summed."""
    table = _table(
        [
            _entry(DataFileContent.POSITION_DELETES, (1,), 7, records=4),
            _entry(DataFileContent.POSITION_DELETES, (1,), 7, records=6, file_format=FileFormat.PUFFIN),
        ]
    )

    (partition,) = observation_from_table(cast("Table", table)).partitions

    assert partition["position_delete_file_count"] == 2
    assert partition["deletion_vector_count"] == 1
    assert partition["position_delete_record_count"] == 10


def test_equality_delete_records_are_summed() -> None:
    """The records of a partition's equality delete files are added up."""
    table = _table(
        [
            _entry(DataFileContent.EQUALITY_DELETES, (1,), 7, records=2),
            _entry(DataFileContent.EQUALITY_DELETES, (1,), 7, records=5),
        ]
    )

    (partition,) = observation_from_table(cast("Table", table)).partitions

    assert partition["equality_delete_record_count"] == 7


def test_manifest_entry_counts_default_to_zero_when_the_manifest_list_has_none() -> None:
    """A manifest list without entry counts reads as zero entries."""
    table = _table([_entry(DataFileContent.DATA, (1,), 1)])

    assert observation_from_table(cast("Table", table)).manifests == [
        {"length_bytes": 10, "added_entries": 0, "existing_entries": 0, "deleted_entries": 0}
    ]
