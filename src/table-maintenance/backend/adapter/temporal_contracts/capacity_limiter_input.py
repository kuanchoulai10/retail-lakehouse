"""Define the CapacityLimiterInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapacityLimiterInput:
    """Carry the capacity limit and holders across continue-as-new."""

    max_concurrent: int
    holders: list[str] = field(default_factory=list)
