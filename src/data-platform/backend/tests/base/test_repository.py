"""Tests for Repository base type."""

from dataclasses import dataclass

import pytest
from base import Entity, EntityId, Repository


@dataclass(frozen=True)
class ItemId(EntityId):
    """Test stub for EntityId."""

    pass


@dataclass(eq=False)
class Item(Entity[ItemId]):
    """Test stub for Entity."""

    id: ItemId
    name: str


def test_repository_is_abstract():
    """Verify that Repository cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Repository()  # type: ignore[call-arg]


def test_repository_is_generic_over_entity():
    """A concrete repo parameterized with Entity should be instantiable."""

    class InMemoryItemRepo(Repository[Item]):
        def __init__(self) -> None:
            self._items: dict[EntityId, Item] = {}

        def create(self, entity: Item) -> Item:
            self._items[entity.id] = entity
            return entity

        def get(self, entity_id: EntityId) -> Item:
            return self._items[entity_id]

        def list_all(self) -> list[Item]:
            return list(self._items.values())

        def delete(self, entity_id: EntityId) -> None:
            del self._items[entity_id]

    repo = InMemoryItemRepo()
    item = Item(id=ItemId("1"), name="Widget")
    assert repo.create(item) == item
    assert repo.get(ItemId("1")) == item
    assert repo.list_all() == [item]
    repo.delete(ItemId("1"))
    assert repo.list_all() == []


def test_repository_has_abstract_methods():
    """Repository requires create, get, list_all to be implemented."""

    class IncompleteRepo(Repository[Item]):
        pass

    with pytest.raises(TypeError):
        IncompleteRepo()  # type: ignore[abstract]
