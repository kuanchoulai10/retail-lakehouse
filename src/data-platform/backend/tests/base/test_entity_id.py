"""Tests for the Pydantic EntityId base type."""

from __future__ import annotations

import uuid
from typing import ClassVar

import pytest

from base import EntityId, InvariantViolation, ValueObject
from shared_kernel import prefixed_id_pattern

RUN_ID = "mr-01h2xcejqtf2nbrexx3vqjhp41"


class _Id(EntityId):
    """Test stub for EntityId."""


class _OtherId(EntityId):
    """A second EntityId kind with the same raw values."""


class _RunId(EntityId):
    """A prefixed EntityId kind."""

    PREFIX: ClassVar[str | None] = "mr"


class _Holder(ValueObject):
    """A value object holding a prefixed id."""

    run_id: _RunId


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
    with pytest.raises(AttributeError, match="is immutable"):
        identifier.root = "b"


def test_strict_rejects_a_non_string() -> None:
    """Strict mode rejects an int where a string is expected."""
    with pytest.raises(InvariantViolation):
        _Id.model_validate(1)


def test_third_level_subclass_is_rejected() -> None:
    """A concrete id extends EntityId directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_Id):
            pass


@pytest.mark.parametrize(
    "build",
    [
        _RunId,
        _RunId.model_validate,
        lambda value: _RunId.model_validate_json(f'"{value}"'),
    ],
    ids=["positional", "model_validate", "model_validate_json"],
)
def test_prefixed_id_refuses_a_uuid(build) -> None:
    """Every way of building a prefixed id refuses a bare UUID, naming the class and the expected shape."""
    with pytest.raises(InvariantViolation, match=r"^_RunId must look like mr-<26 base32 characters>$"):
        build(str(uuid.uuid4()))


@pytest.mark.parametrize(
    "value",
    [
        "dp-01h2xcejqtf2nbrexx3vqjhp41",
        RUN_ID + "\n",
        RUN_ID.upper(),
        "mr-81h2xcejqtf2nbrexx3vqjhp41",
        RUN_ID[:-1],
        "",
    ],
    ids=["other prefix", "trailing newline", "upper case", "first character above 7", "short", "empty"],
)
def test_prefixed_id_refuses_any_other_shape(value: str) -> None:
    """A prefixed id refuses a value of another prefix or of the wrong suffix."""
    with pytest.raises(InvariantViolation, match="_RunId must look like mr-"):
        _RunId(value)


def test_prefixed_id_accepts_its_shape() -> None:
    """A value of the declared prefix and a valid suffix is accepted on every path."""
    assert _RunId(RUN_ID).value == RUN_ID
    assert _RunId.model_validate(RUN_ID) == _RunId(RUN_ID)
    assert _RunId.model_validate_json(f'"{RUN_ID}"') == _RunId(RUN_ID)


def test_prefixed_id_nested_in_a_value_object_is_checked() -> None:
    """A wrong id inside a value object read from primitives is refused too."""
    with pytest.raises(InvariantViolation, match="must look like mr-"):
        _Holder.from_primitives({"run_id": str(uuid.uuid4())})


def test_prefix_does_not_change_the_wire_form() -> None:
    """``PREFIX`` is not a field: the id dumps, serializes and prints as its bare string."""
    identifier = _RunId(RUN_ID)

    assert identifier.model_dump() == RUN_ID
    assert identifier.model_dump_json() == f'"{RUN_ID}"'
    assert str(identifier) == RUN_ID
    assert set(_RunId.model_fields) == {"root"}


def test_new_mints_a_valid_id() -> None:
    """``new()`` returns an id of the class, matching the prefix pattern, a fresh one each call."""
    minted = _RunId.new()

    assert type(minted) is _RunId
    assert prefixed_id_pattern("mr").fullmatch(minted.value)
    assert _RunId.new() != minted


def test_unprefixed_id_accepts_any_string() -> None:
    """An id kind without ``PREFIX`` accepts any string, including a UUID and the empty string."""
    assert _Id.PREFIX is None
    assert _Id(str(uuid.uuid4())).value
    assert _Id("").value == ""
    assert _Id(RUN_ID).value == RUN_ID


def test_new_without_prefix_is_type_error() -> None:
    """``new()`` on an id kind without ``PREFIX`` raises ``TypeError`` naming the class."""
    with pytest.raises(TypeError, match="_Id has no PREFIX"):
        _Id.new()


def test_an_invalid_prefix_is_refused_when_the_class_is_defined() -> None:
    """A ``PREFIX`` that is not 2 to 8 lowercase letters fails at class definition."""
    with pytest.raises(ValueError, match="prefix must be 2 to 8 lowercase letters"):

        class _BadId(EntityId):
            PREFIX: ClassVar[str | None] = "MR"
