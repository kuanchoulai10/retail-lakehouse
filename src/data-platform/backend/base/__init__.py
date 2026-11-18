"""Domain-Driven Design building blocks.

Provides the foundational tactical patterns for structuring domain models,
built on Pydantic v2:

- ValueObject: frozen, strict value with no identity; reads and writes its
  wire form through ``from_primitives`` / ``to_primitives`` and makes a changed
  copy through ``with_changes``, which runs every validator.
- EntityId: a typed string identifier for an Entity, built positionally.
- Entity: an object with identity, equal by class and ``id``; every
  assignment is validated and atomic.
- AggregateRoot: an Entity that acts as the entry point and consistency
  boundary for a cluster of related objects, and collects DomainEvents.
- DomainEvent: a frozen record of something that happened, timestamped.
- InvariantViolation: the ValueError every model base raises for refused
  data, its string one line naming the first problem; Pydantic's
  ValidationError never leaves the bases.
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
from base.invariant_violation import InvariantViolation
from base.repository import Repository
from base.store import Store
from base.use_case import UseCase
from base.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "EntityId",
    "EventDispatcher",
    "EventHandler",
    "Gateway",
    "InvariantViolation",
    "Repository",
    "Store",
    "UseCase",
    "ValueObject",
]
