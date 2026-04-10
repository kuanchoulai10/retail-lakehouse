from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from base.entity import Entity

if TYPE_CHECKING:
    from base.domain_event import DomainEvent


@dataclass(eq=False)
class AggregateRoot(Entity):
    """Entity that serves as a consistency boundary and emits domain events.

    Subclasses should use @dataclass(eq=False) to preserve identity-based equality.
    """

    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def register_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
