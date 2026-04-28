"""Define the TableProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.read_properties import (
    ReadProperties,
)
from application.domain.model.catalog.table_properties.write_properties import (
    WriteProperties,
)


@dataclass(frozen=True)
class TableProperties(ValueObject):
    """Top-level container for all Iceberg table properties."""

    format_version: int | None = None
    write: WriteProperties | None = None
    read: ReadProperties | None = None
