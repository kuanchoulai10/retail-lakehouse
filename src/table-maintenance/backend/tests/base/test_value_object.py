"""Tests for ValueObject base type."""

from abc import ABC
from dataclasses import dataclass

from base import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    amount: int
    currency: str


def test_value_object_is_abstract():
    assert issubclass(ValueObject, ABC)


def test_equal_by_value():
    a = Money(amount=100, currency="USD")
    b = Money(amount=100, currency="USD")
    assert a == b


def test_not_equal_different_value():
    a = Money(amount=100, currency="USD")
    b = Money(amount=200, currency="USD")
    assert a != b


def test_hash_by_value():
    a = Money(amount=100, currency="USD")
    b = Money(amount=100, currency="USD")
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_immutable():
    m = Money(amount=100, currency="USD")
    import pytest

    with pytest.raises(AttributeError):
        m.amount = 200  # type: ignore[misc]  # ty: ignore[invalid-assignment]
