"""Tests for EntityId base type."""

from dataclasses import dataclass

from base import EntityId, ValueObject


@dataclass(frozen=True)
class UserId(EntityId):
    pass


@dataclass(frozen=True)
class OrderId(EntityId):
    pass


def test_entity_id_is_value_object():
    assert issubclass(EntityId, ValueObject)


def test_has_value():
    uid = UserId(value="user-1")
    assert uid.value == "user-1"


def test_str_returns_value():
    uid = UserId(value="user-1")
    assert str(uid) == "user-1"


def test_equal_same_type_same_value():
    a = UserId(value="1")
    b = UserId(value="1")
    assert a == b


def test_not_equal_different_value():
    a = UserId(value="1")
    b = UserId(value="2")
    assert a != b


def test_different_id_types_not_equal():
    """UserId('1') != OrderId('1') even though value is the same."""
    u = UserId(value="1")
    o = OrderId(value="1")
    assert u != o
