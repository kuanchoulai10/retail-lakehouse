"""Tests for the Pydantic EntityId base type."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from base import EntityId, ValueObject


class _Id(EntityId):
    """Test stub for EntityId."""


class _OtherId(EntityId):
    """A second EntityId kind with the same raw values."""


class _Pair(ValueObject):
    """A two-field value object built by keyword."""

    name: str
    count: int


def test_positional_construction_type_checks() -> None:
    """An id is built positionally and a value object by keyword, and both type-check."""
    identifier = _Id("a")
    pair = _Pair(name="n", count=1)
    assert identifier.value == "a"
    assert pair.count == 1


def test_value_returns_the_raw_string() -> None:
    """``value`` is the wrapped string."""
    assert _Id("a").value == "a"


def test_str_returns_the_value() -> None:
    """``str()`` is the raw identifier."""
    assert str(_Id("a")) == "a"


def test_same_kind_same_value_is_equal() -> None:
    """Two ids of one kind with one value are equal."""
    assert _Id("a") == _Id("a")


def test_different_value_is_not_equal() -> None:
    """Two ids of one kind with different values differ."""
    assert _Id("a") != _Id("b")


def test_different_kind_same_value_is_not_equal() -> None:
    """Ids of different kinds never compare equal."""
    assert _Id("a") != _OtherId("a")


def test_is_hashable() -> None:
    """Equal ids collapse in a set."""
    assert {_Id("a"), _Id("a")} == {_Id("a")}


def test_is_frozen() -> None:
    """An id cannot be reassigned."""
    identifier = _Id("a")
    with pytest.raises(ValidationError):
        identifier.root = "b"


def test_strict_rejects_a_non_string() -> None:
    """Strict mode rejects an int where a string is expected."""
    with pytest.raises(ValidationError):
        _Id.model_validate(1)


def test_third_level_subclass_is_rejected() -> None:
    """A concrete id extends EntityId directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_Id):
            pass
