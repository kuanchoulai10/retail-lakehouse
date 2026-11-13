"""Define the CandidateScore value object."""

from __future__ import annotations

from pydantic import Field, NonNegativeFloat, NonNegativeInt

from base import ValueObject


class CandidateScore(ValueObject):
    """Say how much a compaction of a partition is worth and what it is estimated to cost.

    ``reducible_files`` is the benefit (the files a compaction could remove),
    ``estimated_gb_hours`` the cost, from ``data_bytes``; ``score`` weighs both
    against fixed reference bounds, so it means the same on every table.
    """

    reducible_files: NonNegativeInt
    data_bytes: NonNegativeInt
    estimated_gb_hours: NonNegativeFloat
    score: float = Field(ge=0.0, le=1.0)
