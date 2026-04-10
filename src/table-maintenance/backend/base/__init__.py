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
"""

from base.aggregate_root import AggregateRoot
from base.domain_event import DomainEvent
from base.entity import Entity
from base.entity_id import EntityId
from base.repository import Repository
from base.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "EntityId",
    "Repository",
    "ValueObject",
]
