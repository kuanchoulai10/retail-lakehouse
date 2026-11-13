"""Define the PriorityWeightSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class PriorityWeightSettings(BaseModel):
    """How much each policy priority multiplies a candidate's score when a compaction round ranks candidates."""

    p0: float = 4.0
    p1: float = 2.0
    p2: float = 1.0
