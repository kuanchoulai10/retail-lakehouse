"""Define the GenericTable aggregate root."""

from __future__ import annotations

from pydantic import Field

from base.model import AggregateRoot
from context.catalog.application.domain.model.generic_table.generic_table_id import GenericTableId


class GenericTable(AggregateRoot[GenericTableId]):
    """A non-Iceberg table the catalog registers: its format, base location, doc and properties.

    It has no schema, no snapshots and no uuid, and the catalog cannot rename or edit it.
    """

    id: GenericTableId
    format: str
    base_location: str | None
    doc: str | None
    properties: dict[str, str] = Field(default_factory=dict)
