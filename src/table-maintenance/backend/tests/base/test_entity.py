"""Tests for Entity base type."""

from dataclasses import dataclass

from core.base import Entity, EntityId


@dataclass(frozen=True)
class UserId(EntityId):
    """Test stub for EntityId."""

    pass


@dataclass(eq=False)
class User(Entity[UserId]):
    """Test stub for Entity."""

    id: UserId
    name: str
    email: str


def test_entity_is_base_class():
    """Verify that Entity is a subclass of ABC."""
    from abc import ABC

    assert issubclass(Entity, ABC)


def test_equal_by_id():
    """Verify that two Entities with the same id are equal."""
    a = User(id=UserId("1"), name="Alice", email="a@example.com")
    b = User(id=UserId("1"), name="Bob", email="b@example.com")
    assert a == b


def test_not_equal_different_id():
    """Verify that two Entities with different ids are not equal."""
    a = User(id=UserId("1"), name="Alice", email="a@example.com")
    b = User(id=UserId("2"), name="Alice", email="a@example.com")
    assert a != b


def test_hash_by_id():
    """Verify that Entities with the same id produce the same hash."""
    a = User(id=UserId("1"), name="Alice", email="a@example.com")
    b = User(id=UserId("1"), name="Bob", email="b@example.com")
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_not_equal_to_other_types():
    """Verify that an Entity is not equal to non-Entity types."""
    a = User(id=UserId("1"), name="Alice", email="a@example.com")
    assert a != "1"
    assert a != 1


def test_entity_is_not_a_dataclass():
    """Entity itself should be a plain class, not a dataclass."""
    import dataclasses

    assert not dataclasses.is_dataclass(Entity)
