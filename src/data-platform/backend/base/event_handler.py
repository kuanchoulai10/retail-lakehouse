"""Define the EventHandler abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from base._inheritance_guard import enforce_max_depth
from base.domain_event import DomainEvent

E = TypeVar("E", bound=DomainEvent)


class EventHandler(ABC, Generic[E]):
    """Abstract handler for a specific domain event type."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Enforce flat hierarchy: concrete handlers extend EventHandler directly (max depth 1)."""
        super().__init_subclass__(**kwargs)
        enforce_max_depth(cls, EventHandler, 1)

    @abstractmethod
    def handle(self, event: E) -> None:
        """Process the given domain event."""
