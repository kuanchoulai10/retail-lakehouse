"""Define the EventHandler abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from base.domain_event import DomainEvent

E = TypeVar("E", bound=DomainEvent)


class EventHandler(ABC, Generic[E]):
    """Abstract handler for a specific domain event type."""

    @abstractmethod
    def handle(self, event: E) -> None:
        """Process the given domain event."""
