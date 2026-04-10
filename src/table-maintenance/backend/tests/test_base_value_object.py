"""Tests for ValueObject base type."""

from dataclasses import FrozenInstanceError, dataclass

import pytest
from base import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    amount: int
    currency: str


def test_value_object_is_base_class():
    """ValueObject should be an ABC base class."""
    from abc import ABC

    assert issubclass(ValueObject, ABC)


def test_equal_by_value():
    a = Money(amount=100, currency="USD")
    b = Money(amount=100, currency="USD")
    assert a == b


def test_not_equal_when_different():
    a = Money(amount=100, currency="USD")
    b = Money(amount=200, currency="USD")
    assert a != b


def test_immutable():
    """ValueObject should be frozen (immutable)."""
    m = Money(amount=100, currency="USD")
    with pytest.raises(FrozenInstanceError):
        m.amount = 999  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_hashable():
    """ValueObjects with same values should have same hash."""
    a = Money(amount=100, currency="USD")
    b = Money(amount=100, currency="USD")
    assert hash(a) == hash(b)
    assert len({a, b}) == 1
