"""Define the PartitionStats value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject


class PartitionStats(ValueObject):
    """Hold file statistics of one partition, values in Iceberg's internal form.

    ``last_written_at`` is when a writer last added a live file to the partition
    (compactions do not count), or None when that is unknown.
    """

    spec_id: int
    values: tuple[str | int | float | bool | None, ...]
    data_file_count: int
    position_delete_file_count: int
    equality_delete_file_count: int
    total_data_file_size_bytes: int
    last_written_at: datetime | None = None
