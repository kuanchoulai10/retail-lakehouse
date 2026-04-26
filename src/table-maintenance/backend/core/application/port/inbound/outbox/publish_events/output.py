"""Define the PublishEventsResult."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishEventsResult:
    """Result of one outbox publishing tick."""

    published_count: int
