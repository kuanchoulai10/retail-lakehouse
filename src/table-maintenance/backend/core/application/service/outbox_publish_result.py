"""Define the OutboxPublishResult."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutboxPublishResult:
    """Result of one outbox publishing tick."""

    published_count: int
