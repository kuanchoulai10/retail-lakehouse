"""Define the ReadParquetProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ReadParquetProperties(ValueObject):
    """Parquet read optimization properties."""

    vectorization_enabled: bool | None = None
    batch_size: int | None = None
