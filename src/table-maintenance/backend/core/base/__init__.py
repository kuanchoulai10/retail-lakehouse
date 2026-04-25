"""Domain-Driven Design building blocks.

Provides the foundational tactical patterns for structuring domain models:

- ValueObject: Describes a characteristic or measurement with no identity.
- EntityId: A typed identifier for an Entity, implemented as a ValueObject.
- Entity: An object with a distinct identity that persists over time.
- AggregateRoot: An Entity that acts as the entry point and consistency
  boundary for a cluster of related objects.
- DomainEvent: A record of something meaningful that occurred in the domain.
- Repository: An interface for retrieving and persisting aggregates/entities,
  decoupling the domain from infrastructure concerns.
- UseCase: A single application-level operation that orchestrates domain
  objects and repositories to fulfil a business action.
- EventHandler: An abstract handler for a specific domain event type.
- EventDispatcher: Routes domain events to registered handlers.
"""

from core.base.aggregate_root import AggregateRoot
from core.base.domain_event import DomainEvent
from core.base.entity import Entity
from core.base.entity_id import EntityId
from core.base.event_dispatcher import EventDispatcher
from core.base.event_handler import EventHandler
from core.base.repository import Repository
from core.base.use_case import UseCase
from core.base.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "EntityId",
    "EventDispatcher",
    "EventHandler",
    "Repository",
    "UseCase",
    "ValueObject",
]
