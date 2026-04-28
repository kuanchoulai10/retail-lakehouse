"""Define the ParquetProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ParquetProperties(ValueObject):
    """Parquet file format tuning properties."""

    compression_codec: str | None = None
    compression_level: int | None = None
    row_group_size_bytes: int | None = None
    page_size_bytes: int | None = None
    dict_size_bytes: int | None = None
