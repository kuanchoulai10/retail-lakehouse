"""Define the JobPartitionField."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobPartitionField:
    """Name one field of a partition spec: its source column, the column's type and the transform.

    ``source_column`` is dot-joined for a nested column, ``source_type`` and ``transform`` are
    Iceberg's text (``timestamptz``, ``day``, ``bucket[16]``).
    """

    source_column: str
    source_type: str
    transform: str
