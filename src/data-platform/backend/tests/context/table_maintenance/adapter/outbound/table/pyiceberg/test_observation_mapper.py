"""Test when the observation mapper says each partition was last written."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from pyiceberg.manifest import (
    DataFile,
    DataFileContent,
    ManifestEntry,
    ManifestEntryStatus,
)
from pyiceberg.table.snapshots import Operation, Summary
from pyiceberg.typedef import Record

from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    observation_from_table,
)

if TYPE_CHECKING:
    from pyiceberg.table import Table

T1 = 1_767_225_600_000
T2 = T1 + 60_000
T3 = T1 + 120_000


def _entry(partition: tuple[Any, ...], snapshot_id: int, content: DataFileContent = DataFileContent.DATA):  # noqa: ANN202
    data_file = DataFile.from_args(
        content=content,
        partition=Record(*partition),
        file_size_in_bytes=10,
        record_count=1,
    )
    data_file.spec_id = 0
    return ManifestEntry.from_args(status=ManifestEntryStatus.ADDED, snapshot_id=snapshot_id, data_file=data_file)


def _snapshot(snapshot_id: int, timestamp_ms: int, operation: Operation = Operation.APPEND) -> SimpleNamespace:
    return SimpleNamespace(snapshot_id=snapshot_id, timestamp_ms=timestamp_ms, summary=Summary(operation))


def _table(entries: list[ManifestEntry], snapshots: list[SimpleNamespace]) -> SimpleNamespace:
    manifest = SimpleNamespace(
        manifest_length=10,
        added_files_count=None,
        existing_files_count=None,
        deleted_files_count=None,
        partition_spec_id=0,
        fetch_manifest_entry=lambda io, discard_deleted=True: entries,
    )
    current = SimpleNamespace(snapshot_id=snapshots[-1].snapshot_id, manifests=lambda io: [manifest], timestamp_ms=0)
    by_id = {s.snapshot_id: s for s in snapshots}
    return SimpleNamespace(
        io=None,
        metadata=SimpleNamespace(
            table_uuid="u",
            properties={},
            partition_specs=[],
            snapshots=snapshots,
            snapshot_by_id=by_id.get,
        ),
        current_snapshot=lambda: current,
    )


def _last_written(table: SimpleNamespace) -> dict[tuple[Any, ...], str | None]:
    observation = observation_from_table(cast("Table", table))
    return {tuple(p["values"]): p["last_written_at"] for p in observation.partitions}


def test_partition_last_written_at_is_the_newest_adding_snapshot() -> None:
    """A partition was last written by the newest snapshot that added one of its live files."""
    table = _table(
        [_entry(("a",), 1), _entry(("a",), 2), _entry(("b",), 1)],
        [_snapshot(1, T1), _snapshot(2, T2)],
    )

    assert _last_written(table) == {
        ("a",): "2026-01-01T00:01:00+00:00",
        ("b",): "2026-01-01T00:00:00+00:00",
    }


def test_last_written_at_is_none_when_the_snapshot_is_gone() -> None:
    """A partition whose files came from an expired snapshot has no known last write."""
    table = _table([_entry(("a",), 99)], [_snapshot(1, T1)])

    assert _last_written(table) == {("a",): None}


def test_delete_files_count_as_writes() -> None:
    """A delete file added to a partition is a write to it."""
    table = _table(
        [_entry(("a",), 1), _entry(("a",), 2, DataFileContent.POSITION_DELETES)],
        [_snapshot(1, T1), _snapshot(2, T2, Operation.DELETE)],
    )

    assert _last_written(table) == {("a",): "2026-01-01T00:01:00+00:00"}


def test_compaction_snapshots_are_not_writes() -> None:
    """Files a compaction (a replace snapshot) added do not make the partition recently written."""
    table = _table(
        [_entry(("a",), 3), _entry(("b",), 3), _entry(("b",), 2)],
        [_snapshot(1, T1), _snapshot(2, T2), _snapshot(3, T3, Operation.REPLACE)],
    )

    assert _last_written(table) == {("a",): None, ("b",): "2026-01-01T00:01:00+00:00"}
