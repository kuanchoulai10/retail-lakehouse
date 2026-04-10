"""Tests for Entity base type."""

from base import Entity


class User(Entity):
    id: str
    name: str
    email: str


def test_entity_is_base_class():
    from abc import ABC

    assert issubclass(Entity, ABC)


def test_equal_by_id():
    a = User(id="1", name="Alice", email="a@example.com")
    b = User(id="1", name="Bob", email="b@example.com")
    assert a == b


def test_not_equal_different_id():
    a = User(id="1", name="Alice", email="a@example.com")
    b = User(id="2", name="Alice", email="a@example.com")
    assert a != b


def test_hash_by_id():
    a = User(id="1", name="Alice", email="a@example.com")
    b = User(id="1", name="Bob", email="b@example.com")
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_not_equal_to_other_types():
    a = User(id="1", name="Alice", email="a@example.com")
    assert a != "1"
    assert a != 1
