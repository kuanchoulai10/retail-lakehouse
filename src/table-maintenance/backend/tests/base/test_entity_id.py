"""Tests for EntityId base type."""

from dataclasses import dataclass

from base import EntityId, ValueObject


@dataclass(frozen=True)
class UserId(EntityId):
    """Test stub for EntityId."""

    pass


@dataclass(frozen=True)
class OrderId(EntityId):
    """Test stub for EntityId."""

    pass


def test_entity_id_is_value_object():
    """Verify that EntityId is a subclass of ValueObject."""
    assert issubclass(EntityId, ValueObject)


def test_has_value():
    """Verify that EntityId stores its value."""
    uid = UserId(value="user-1")
    assert uid.value == "user-1"


def test_str_returns_value():
    """Verify that str() returns the underlying value."""
    uid = UserId(value="user-1")
    assert str(uid) == "user-1"


def test_equal_same_type_same_value():
    """Verify that two EntityIds of the same type and value are equal."""
    a = UserId(value="1")
    b = UserId(value="1")
    assert a == b


def test_not_equal_different_value():
    """Verify that two EntityIds with different values are not equal."""
    a = UserId(value="1")
    b = UserId(value="2")
    assert a != b


def test_different_id_types_not_equal():
    """UserId('1') != OrderId('1') even though value is the same."""
    u = UserId(value="1")
    o = OrderId(value="1")
    assert u != o
