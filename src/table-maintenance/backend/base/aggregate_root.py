from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from base.entity import Entity

if TYPE_CHECKING:
    from base.domain_event import DomainEvent


class AggregateRoot(Entity):
    """Entity that serves as a consistency boundary and emits domain events."""

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def register_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
