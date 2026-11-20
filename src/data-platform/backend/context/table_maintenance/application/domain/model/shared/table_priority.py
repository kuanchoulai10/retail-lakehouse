"""Define the TablePriority enumeration."""

from __future__ import annotations

from enum import StrEnum


class TablePriority(StrEnum):
    """Enumerate how urgently a table's maintenance is scheduled, P0 most urgent, P3 the default."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

    @classmethod
    def default(cls) -> TablePriority:
        """Return the priority a table starts at, P3."""
        return cls.P3

    def outranks(self, other: TablePriority) -> bool:
        """Tell whether this priority is more urgent than ``other``; P0 outranks P1, and none outranks itself."""
        order = list(TablePriority)
        return order.index(self) < order.index(other)
