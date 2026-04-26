"""Define the OutboxEntry value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.value_object import ValueObject

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class OutboxEntry(ValueObject):
    """An immutable record of a domain event pending publication."""

    id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: str
    occurred_at: datetime
    published_at: datetime | None = None
