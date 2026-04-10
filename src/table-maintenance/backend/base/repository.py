from __future__ import annotations

from abc import ABC, abstractmethod

from base.entity import Entity


class Repository[E: Entity](ABC):
    """Generic persistence interface for entities."""

    @abstractmethod
    def create(self, entity: E) -> E: ...

    @abstractmethod
    def get(self, entity_id: str) -> E: ...

    @abstractmethod
    def list_all(self) -> list[E]: ...

    @abstractmethod
    def delete(self, entity_id: str) -> None: ...
