"""Define the ReadProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.read_orc_properties import (
    ReadOrcProperties,
)
from application.domain.model.catalog.table_properties.read_parquet_properties import (
    ReadParquetProperties,
)
from application.domain.model.catalog.table_properties.split_properties import (
    SplitProperties,
)


@dataclass(frozen=True)
class ReadProperties(ValueObject):
    """All read-related table properties."""

    split: SplitProperties | None = None
    parquet: ReadParquetProperties | None = None
    orc: ReadOrcProperties | None = None
