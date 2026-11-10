"""Domain-Driven Design building blocks.

Provides the foundational tactical patterns for structuring domain models,
built on Pydantic v2:

- ValueObject: frozen, strict value with no identity; reads and writes its
  wire form through ``from_primitives`` / ``to_primitives``.
- EntityId: a typed string identifier for an Entity, built positionally.
- Entity: an object with identity, equal by class and ``id``; every
  assignment is validated and atomic.
- AggregateRoot: an Entity that acts as the entry point and consistency
  boundary for a cluster of related objects, and collects DomainEvents.
- DomainEvent: a frozen record of something that happened, timestamped.
- WholeSeconds: a ``timedelta`` written as integer seconds on the wire.
- validated_copy: a copy with changes that runs every validator.
- validation_message: a one-line message for a validation error.
- Repository: an interface for retrieving and persisting aggregates/entities,
  decoupling the domain from infrastructure concerns.
- UseCase: a single application-level operation that orchestrates domain
  objects and repositories to fulfil a business action.
- Gateway / Store: outbound ports for other systems and stored state.
- EventHandler: an abstract handler for a specific domain event type.
- EventDispatcher: routes domain events to registered handlers.
"""

from __future__ import annotations

from base.aggregate_root import AggregateRoot
from base.domain_event import DomainEvent
from base.entity import Entity
from base.entity_id import EntityId
from base.event_dispatcher import EventDispatcher
from base.event_handler import EventHandler
from base.gateway import Gateway
from base.repository import Repository
from base.store import Store
from base.use_case import UseCase
from base.validated_copy import validated_copy
from base.validation_message import validation_message
from base.value_object import ValueObject
from base.whole_seconds import WholeSeconds

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "EntityId",
    "EventDispatcher",
    "EventHandler",
    "Gateway",
    "Repository",
    "Store",
    "UseCase",
    "ValueObject",
    "WholeSeconds",
    "validated_copy",
    "validation_message",
]
