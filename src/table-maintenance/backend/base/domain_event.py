from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class DomainEvent(ABC):  # noqa: B024
    """Something that happened in the domain.

    Subclasses should use @dataclass(frozen=True) to enforce immutability.
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)
