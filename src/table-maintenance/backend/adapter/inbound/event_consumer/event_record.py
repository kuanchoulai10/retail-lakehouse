"""Define the EventRecord a source hands to the consumer loop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventRecord:
    """Carry one consumed record and its position in the source."""

    value: bytes | None
    topic: str
    partition: int
    offset: int
