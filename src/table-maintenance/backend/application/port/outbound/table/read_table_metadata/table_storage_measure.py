"""Define the TableStorageMeasure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableStorageMeasure:
    """The bytes and files of a table.

    ``current`` covers the data and delete files of the current snapshot;
    ``referenced`` covers every distinct file any snapshot still references.
    """

    current_bytes: int
    current_files: int
    referenced_bytes: int
    referenced_files: int
