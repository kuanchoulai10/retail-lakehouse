"""Define the MaintenancePriority enumeration."""

from __future__ import annotations

from enum import StrEnum


class MaintenancePriority(StrEnum):
    """Enumerate how urgent a policy's tables are when compaction rounds share their budget.

    ``P0`` is the most urgent and ``P2`` the least; every priority has a weight
    that multiplies a candidate's score, and an SLA after which a candidate
    still waiting is overdue.
    """

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
