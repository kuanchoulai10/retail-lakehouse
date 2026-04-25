"""Tests for ValueObject base type."""

from abc import ABC
from dataclasses import dataclass

from core.base import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    """Test stub for ValueObject."""

    amount: int
    currency: str


def test_value_object_is_abstract():
    """Verify that ValueObject is a subclass of ABC."""
    assert issubclass(ValueObject, ABC)


def test_equal_by_value():
    """Verify that two ValueObjects with the same fields are equal."""
    a = Money(amount=100, currency="USD")
    b = Money(amount=100, currency="USD")
    assert a == b


def test_not_equal_different_value():
    """Verify that two ValueObjects with different fields are not equal."""
    a = Money(amount=100, currency="USD")
    b = Money(amount=200, currency="USD")
    assert a != b


def test_hash_by_value():
    """Verify that equal ValueObjects produce the same hash."""
    a = Money(amount=100, currency="USD")
    b = Money(amount=100, currency="USD")
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_immutable():
    """Verify that ValueObject fields cannot be reassigned."""
    m = Money(amount=100, currency="USD")
    import pytest

    with pytest.raises(AttributeError):
        m.amount = 200  # type: ignore[misc]  # ty: ignore[invalid-assignment]
