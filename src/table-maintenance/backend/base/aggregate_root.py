from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from base.entity import Entity

if TYPE_CHECKING:
    from base.domain_event import DomainEvent


@dataclass(eq=False)
class AggregateRoot(Entity):
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
        class Order(AggregateRoot):
            total: int

    Subclasses must use @dataclass(eq=False) to preserve identity-based equality.
    """

    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def register_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
