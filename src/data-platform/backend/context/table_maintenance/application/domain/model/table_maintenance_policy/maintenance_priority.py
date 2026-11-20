"""Define the MaintenancePriority enumeration."""

from __future__ import annotations

from enum import StrEnum


class MaintenancePriority(StrEnum):
    """Enumerate the priority a maintenance policy names.

    ``P0`` is the most urgent and ``P2`` the least. The policy's priority no longer
    orders maintenance: a table's own priority does, in its Volcano queue; KCL-91
    removes this one.
    """

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
