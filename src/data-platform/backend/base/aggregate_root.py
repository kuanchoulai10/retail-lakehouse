"""Define the Pydantic AggregateRoot base class."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from base.entity import Entity
from base.entity_id import EntityId

if TYPE_CHECKING:
    from base.domain_event import DomainEvent


class AggregateRoot[ID: EntityId](Entity[ID]):
    """An Entity that is the entry point and consistency boundary of a cluster of objects.

    External code changes the cluster only through the root, so its
    invariants are enforced in one place. The root records DomainEvents
    with ``register_event()``; the caller takes them with
    ``collect_events()`` after the operation. Pending events are a private
    attribute: never dumped, never compared.

    Concrete aggregates extend AggregateRoot directly (max depth 1,
    counted from here rather than from Entity).

    Usage::

        class Order(AggregateRoot[OrderId]):
            total: int
    """

    _depth_base: ClassVar[bool] = True

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def register_event(self, event: DomainEvent) -> None:
        """Append a domain event to be collected later."""
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return all accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events
