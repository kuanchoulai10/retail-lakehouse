"""Define the PartitionStats value object."""

from __future__ import annotations

from base import ValueObject


class PartitionStats(ValueObject):
    """Hold file statistics of one partition, values in Iceberg's internal form."""

    spec_id: int
    values: tuple[str | int | float | bool | None, ...]
    data_file_count: int
    position_delete_file_count: int
    equality_delete_file_count: int
    total_data_file_size_bytes: int
