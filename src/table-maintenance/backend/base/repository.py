from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from base.entity import Entity

if TYPE_CHECKING:
    from base.entity_id import EntityId


class Repository[E: Entity](ABC):
    """An interface for retrieving and persisting Entities.

    The Repository mediates between the domain layer and the data-mapping
    layer, providing a collection-like API for accessing domain objects.
    Domain code depends on this abstraction, not on concrete storage
    (database, API, in-memory dict), keeping the domain free of
    infrastructure concerns.

    Type parameter ``E`` is bound to Entity, ensuring only domain objects
    with identity are managed through repositories.

    Rules:
        - One Repository per Aggregate/Entity type.
        - Domain code depends on the interface, not the implementation.
        - Implementations live in the infrastructure layer (e.g., repos/).
        - Encapsulates query logic: callers don't write SQL or API calls.

    Usage::

        class JobsRepo(Repository[Job]):
            def create(self, entity: Job) -> Job: ...
            def get(self, entity_id: EntityId) -> Job: ...
            def list_all(self) -> list[Job]: ...
            def delete(self, entity_id: EntityId) -> None: ...
    """

    @abstractmethod
    def create(self, entity: E) -> E: ...

    @abstractmethod
    def get(self, entity_id: EntityId) -> E: ...

    @abstractmethod
    def list_all(self) -> list[E]: ...

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None: ...
