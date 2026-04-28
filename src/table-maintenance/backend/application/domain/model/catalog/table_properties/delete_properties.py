"""Define the DeleteProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)
from application.domain.model.catalog.table_properties.parquet_properties import (
    ParquetProperties,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode


@dataclass(frozen=True)
class DeleteProperties(ValueObject):
    """Delete operation properties with additional format and parquet settings."""

    mode: WriteMode | None = None
    isolation_level: IsolationLevel | None = None
    distribution_mode: DistributionMode | None = None
    format_default: str | None = None
    target_file_size_bytes: int | None = None
    parquet: ParquetProperties | None = None
