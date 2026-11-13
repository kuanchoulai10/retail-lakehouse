"""Define the PrioritySlaSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class PrioritySlaSettings(BaseModel):
    """How many seconds a candidate of each policy priority may wait for a run before it is shown overdue."""

    p0: int = 3600
    p1: int = 14400
    p2: int = 28800
