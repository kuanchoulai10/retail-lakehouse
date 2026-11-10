"""Define the SortField value object."""

from __future__ import annotations

from base.model import ValueObject
from context.catalog.application.domain.model.table.null_order import NullOrder
from context.catalog.application.domain.model.table.sort_direction import SortDirection


class SortField(ValueObject):
    """One field of a sort order: the source column id, its transform, direction and null order."""

    source_id: int
    transform: str
    direction: SortDirection
    null_order: NullOrder
