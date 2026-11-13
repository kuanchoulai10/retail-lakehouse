"""Define the CandidateShortfall enumeration."""

from __future__ import annotations

from enum import StrEnum


class CandidateShortfall(StrEnum):
    """Enumerate why a due compaction found no candidate to take.

    ``all_held`` means every qualifying partition is held by a filter (too small,
    or written too recently); ``all_claimed`` means other runs hold the rest.
    """

    ALL_HELD = "all_held"
    ALL_CLAIMED = "all_claimed"
