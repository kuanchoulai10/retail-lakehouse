"""Define the PlatformPriority value object."""

from __future__ import annotations

from base import ValueObject


class PlatformPriority(ValueObject):
    """What one policy priority (``P0`` to ``P2``) means to the scheduler: its score weight and its SLA in seconds."""

    priority: str
    weight: float
    sla_seconds: int
