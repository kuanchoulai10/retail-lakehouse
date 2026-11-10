"""Tests for the Pydantic Entity base type."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from base import Entity, EntityId


class _UserId(EntityId):
    """Test stub for EntityId."""


class _User(Entity[_UserId]):
    """Test stub for Entity."""

    name: str


class _Account(Entity[_UserId]):
    """A second entity kind sharing the id type."""

    name: str


def test_same_id_different_fields_is_equal() -> None:
    """Entities are equal by identity, not by their other fields."""
    assert _User(id=_UserId("1"), name="a") == _User(id=_UserId("1"), name="b")


def test_same_id_hashes_alike() -> None:
    """Entities with one id hash alike."""
    assert hash(_User(id=_UserId("1"), name="a")) == hash(_User(id=_UserId("1"), name="b"))


def test_different_id_is_not_equal() -> None:
    """Entities with different ids differ."""
    assert _User(id=_UserId("1"), name="a") != _User(id=_UserId("2"), name="a")


def test_different_kind_is_not_equal() -> None:
    """Entities of different classes differ even with one id."""
    assert _User(id=_UserId("1"), name="a") != _Account(id=_UserId("1"), name="a")


def test_is_mutable() -> None:
    """An entity accepts a valid assignment."""
    user = _User(id=_UserId("1"), name="a")
    user.name = "b"
    assert user.name == "b"


def test_validates_assignment() -> None:
    """``validate_assignment`` rejects a wrong type."""
    user = _User(id=_UserId("1"), name="a")
    field = "name"
    with pytest.raises(ValidationError):
        setattr(user, field, 1)


def test_a_raw_string_is_read_as_the_id() -> None:
    """Pydantic validates a nested root model from its raw value, even in strict mode."""
    assert _User.model_validate({"id": "1", "name": "a"}).id == _UserId("1")


def test_strict_rejects_a_wrongly_typed_id() -> None:
    """Strict mode still rejects an int where the id's string is expected."""
    with pytest.raises(ValidationError):
        _User.model_validate({"id": 1, "name": "a"})


def test_rejects_an_unknown_key() -> None:
    """``extra="forbid"`` rejects a key that is not a field."""
    with pytest.raises(ValidationError):
        _User.model_validate({"id": _UserId("1"), "name": "a", "colour": "red"})


def test_third_level_subclass_is_rejected() -> None:
    """A concrete entity extends Entity directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_User):
            pass
