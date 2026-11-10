"""Define the TableSummary value object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from base.model import ValueObject

if TYPE_CHECKING:
    from context.catalog.application.domain.model.table.snapshot import Snapshot

_TOTAL_RECORDS = "total-records"
_TOTAL_DATA_FILES = "total-data-files"
_TOTAL_FILES_SIZE = "total-files-size"


def _count(summary: dict[str, str], key: str) -> int | None:
    try:
        return int(summary[key])
    except KeyError, ValueError:
        return None


class TableSummary(ValueObject):
    """The record count, data file count and total file size in bytes of a table's current snapshot.

    Each is None when the snapshot's summary does not report it, or when there is no snapshot.
    """

    total_records: int | None
    total_data_files: int | None
    total_files_size: int | None

    @classmethod
    def of(cls, snapshot: Snapshot | None) -> TableSummary:
        """Read the totals from ``snapshot``'s summary."""
        summary = {} if snapshot is None else snapshot.summary
        return cls(
            total_records=_count(summary, _TOTAL_RECORDS),
            total_data_files=_count(summary, _TOTAL_DATA_FILES),
            total_files_size=_count(summary, _TOTAL_FILES_SIZE),
        )
