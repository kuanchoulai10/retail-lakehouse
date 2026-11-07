"""Define the SortOrder value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.catalog.application.domain.model.table.sort_field import SortField


@dataclass(frozen=True)
class SortOrder(ValueObject):
    """The default sort order of a table; order 0 with no fields means unsorted."""

    order_id: int
    fields: tuple[SortField, ...]

    @classmethod
    def unsorted(cls) -> SortOrder:
        """Return the order of an unsorted table."""
        return cls(order_id=0, fields=())
