"""Define the OperationResult enumeration."""

from __future__ import annotations

from enum import StrEnum


class OperationResult(StrEnum):
    """Enumerate what a reconciliation did about one operation.

    ``all_held`` and ``all_claimed`` are a due compaction that started nothing
    because every candidate was held by a filter or claimed by another run.
    """

    STARTED = "started"
    WOULD_START = "would_start"
    START_FAILED = "start_failed"
    NOT_NEEDED = "not_needed"
    COOLING_DOWN = "cooling_down"
    OFF = "off"
    NOT_CHECKED = "not_checked"
    NEEDS_ATTENTION = "needs_attention"
    ALL_HELD = "all_held"
    ALL_CLAIMED = "all_claimed"
