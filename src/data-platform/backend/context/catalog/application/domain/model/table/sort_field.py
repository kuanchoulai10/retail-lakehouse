"""Define the SortField value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.catalog.application.domain.model.table.null_order import NullOrder
    from context.catalog.application.domain.model.table.sort_direction import SortDirection


@dataclass(frozen=True)
class SortField(ValueObject):
    """One field of a sort order: the source column id, its transform, direction and null order."""

    source_id: int
    transform: str
    direction: SortDirection
    null_order: NullOrder
