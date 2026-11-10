"""Domain-Driven Design building blocks on Pydantic.

The Pydantic counterparts of the dataclass bases in ``base``, with the
same names. Domain models move onto these one aggregate at a time; once
none is left on the dataclass bases, this package replaces them.

- ValueObject: frozen, strict value with no identity; reads and writes its
  wire form through ``from_primitives`` / ``to_primitives``.
- EntityId: a typed string identifier, built positionally.
- Entity: an object with identity, equal by class and ``id``.
- AggregateRoot: an Entity that collects DomainEvents.
- DomainEvent: a frozen record of something that happened, timestamped.
- WholeSeconds: a ``timedelta`` written as integer seconds on the wire.
- validated_copy: a copy with changes that runs every validator.
- validation_message: a one-line message for a validation error.
"""

from __future__ import annotations

from base.model.aggregate_root import AggregateRoot
from base.model.domain_event import DomainEvent
from base.model.entity import Entity
from base.model.entity_id import EntityId
from base.model.validated_copy import validated_copy
from base.model.validation_message import validation_message
from base.model.value_object import ValueObject
from base.model.whole_seconds import WholeSeconds

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "EntityId",
    "ValueObject",
    "WholeSeconds",
    "validated_copy",
    "validation_message",
]
