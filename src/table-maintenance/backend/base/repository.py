"""Define the Repository abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from base._inheritance_guard import enforce_max_depth
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

    The base contract is intentionally minimal: ``create``, ``get``,
    ``list_all``. Mutation and removal are not universal — historical
    aggregates (e.g. JobRun) are append-only and never deleted. Concrete
    repository ports add ``update``, ``delete``, or aggregate-specific
    queries when their aggregate's lifecycle requires them.

    Rules:
        - One Repository per Aggregate/Entity type.
        - Domain code depends on the interface, not the implementation.
        - Implementations live in the infrastructure layer (e.g., repos/).
        - Encapsulates query logic: callers don't write SQL or API calls.

    Usage::

        class JobsRepo(Repository[Job]):
            @abstractmethod
            def update(self, entity: Job) -> Job: ...
            @abstractmethod
            def delete(self, entity_id: EntityId) -> None: ...
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Enforce port + adapter inheritance depth (max 2)."""
        super().__init_subclass__(**kwargs)
        enforce_max_depth(cls, Repository, 2)

    @abstractmethod
    def create(self, entity: E) -> E:
        """Persist a new entity and return it."""

    @abstractmethod
    def get(self, entity_id: EntityId) -> E:
        """Retrieve an entity by its identifier."""

    @abstractmethod
    def list_all(self) -> list[E]:
        """Return all entities of this type."""
