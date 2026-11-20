"""Define the PartitionStats value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import NonNegativeInt

from base import ValueObject


class PartitionStats(ValueObject):
    """Hold file statistics of one partition, values in Iceberg's internal form.

    ``position_delete_file_count`` counts deletion vectors too; ``deletion_vector_count``
    says how many of those files they are, and ``position_delete_record_count`` sums
    the records of both kinds. ``last_written_at`` is when a writer last added a live
    file to the partition (compactions do not count), or None when that is unknown.
    """

    spec_id: int
    values: tuple[str | int | float | bool | None, ...]
    data_file_count: int
    position_delete_file_count: int
    equality_delete_file_count: int
    total_data_file_size_bytes: int
    data_record_count: NonNegativeInt = 0
    position_delete_record_count: NonNegativeInt = 0
    equality_delete_record_count: NonNegativeInt = 0
    deletion_vector_count: NonNegativeInt = 0
    last_written_at: datetime | None = None
