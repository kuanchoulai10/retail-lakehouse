"""Define the AggregateRoot base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.base.entity import Entity
from core.base.entity_id import EntityId

if TYPE_CHECKING:
    from core.base.domain_event import DomainEvent


class AggregateRoot[ID: EntityId](Entity[ID]):
    """An Entity that acts as the entry point and consistency boundary for a cluster of related objects.

    External code should only modify the cluster through the AggregateRoot,
    never by reaching into child Entities or ValueObjects directly. This
    ensures invariants are enforced in one place.

    The AggregateRoot also collects DomainEvents that record what happened
    during a business operation. After the operation completes, the caller
    retrieves the events via ``collect_events()`` and dispatches them.

    Examples: Order (owns OrderLines), Account (owns Transactions).

    Rules:
        - Consistency boundary: all changes within the aggregate are atomic.
        - Single entry point: external code interacts only with the root.
        - Event producer: records DomainEvents via ``register_event()``.
        - collect_events() returns accumulated events and clears the list.

    Usage::

        @dataclass(eq=False)
        class Order(AggregateRoot[OrderId]):
            total: int

    Subclasses must use @dataclass(eq=False) to preserve identity-based equality.
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Initialize subclass and forward keyword arguments to super."""
        super().__init_subclass__(**kwargs)

    def register_event(self, event: DomainEvent) -> None:
        """Append a domain event to be collected later."""
        if not hasattr(self, "_events"):
            self._events: list[DomainEvent] = []
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return all accumulated events and clear the internal list."""
        if not hasattr(self, "_events"):
            return []
        events = list(self._events)
        self._events.clear()
        return events
