from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    observation_from_table,
)
from pyiceberg.manifest import (
    DataFile,
    DataFileContent,
    ManifestEntry,
    ManifestEntryStatus,
)
from pyiceberg.typedef import Record

if TYPE_CHECKING:
    from pyiceberg.table import Table


def _entry(content: DataFileContent, partition: tuple[Any, ...], size: int):  # noqa: ANN202
    data_file = DataFile.from_args(
        content=content,
        partition=Record(*partition),
        file_size_in_bytes=size,
        record_count=1,
    )
    data_file.spec_id = 0
    return ManifestEntry.from_args(status=ManifestEntryStatus.ADDED, data_file=data_file)


def _table(entries: list[ManifestEntry]) -> SimpleNamespace:
    manifest = SimpleNamespace(
        manifest_length=10,
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
        ),
        current_snapshot=lambda: snapshot,
    )


def test_counts_each_content_type_and_sums_only_data_file_sizes() -> None:
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
        },
        {
            "spec_id": 0,
            "values": [2],
            "data_file_count": 0,
            "position_delete_file_count": 1,
            "equality_delete_file_count": 0,
            "total_data_file_size_bytes": 0,
        },
    ]
