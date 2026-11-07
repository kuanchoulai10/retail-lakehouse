"""Define the EventDispatcher for routing domain events to handlers."""

from __future__ import annotations

from base.domain_event import DomainEvent
from base.event_handler import EventHandler


class EventDispatcher:
    """Routes domain events to registered handlers."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        """EventDispatcher is a concrete utility and must not be subclassed."""
        super().__init_subclass__(**kwargs)
        raise TypeError(
            f"EventDispatcher must not be subclassed; got {cls.__qualname__}"
        )

    def __init__(self) -> None:
        """Initialize with an empty handler registry."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def register(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        """Dispatch a single event to all registered handlers for its type."""
        for handler in self._handlers.get(type(event), []):
            handler.handle(event)

    def dispatch_all(self, events: list[DomainEvent]) -> None:
        """Dispatch a list of events in order."""
        for event in events:
            self.dispatch(event)
