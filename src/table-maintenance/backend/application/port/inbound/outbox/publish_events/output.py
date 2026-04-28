"""Define the PublishEventsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishEventsUseCaseOutput:
    """Result of one outbox publishing tick."""

    published_count: int
